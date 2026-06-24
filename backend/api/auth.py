import os
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import User, StudentProfile
from auth.schemas import RegisterRequest, LoginRequest, TokenResponse, GoogleAuthRequest
from auth.security import hash_password, verify_password, create_access_token

# ── Phase 5 imports ───────────────────────────────────────────────────────────
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest

router = APIRouter(prefix="/auth", tags=["Auth"])

# Loaded once at module import. The app will still start if this is unset,
# but every /auth/google call will fail with a clear 500 — better than a
# silent misconfiguration that accepts any token.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Existing endpoints (unchanged) ────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)

    try:
        db.flush()

        student = StudentProfile(
            user_id=user.id,
            name=payload.name,
            email=payload.email,
            password="",
        )
        db.add(student)
        db.commit()
        db.refresh(user)
        db.refresh(student)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    token = create_access_token(user_id=user.id, email=user.email)

    return TokenResponse(
        access_token=token,
        student_id=student.id,
        name=student.name,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    if not user or not user.hashed_password:
        raise invalid_credentials

    if not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated.",
        )

    student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account is missing profile data. Please contact support.",
        )

    token = create_access_token(user_id=user.id, email=user.email)

    return TokenResponse(
        access_token=token,
        student_id=student.id,
        name=student.name,
        email=user.email,
    )


# ── Phase 5: Google OAuth ─────────────────────────────────────────────────────

@router.post("/google", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Accepts a Google ID token (credential) from the frontend GIS widget.

    Flow:
      1. Verify the token signature and claims against GOOGLE_CLIENT_ID.
      2. Extract google_id, email, name from the verified payload.
      3. Look up user by google_id  →  found: use it.
         Look up user by email      →  found: link google_id and use it.
         Neither found              →  create new User + StudentProfile.
      4. Issue our own JWT and return the standard TokenResponse.
    """
    if not GOOGLE_CLIENT_ID:
        # Fail loudly — a misconfigured server should never silently accept tokens.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on this server. Set GOOGLE_CLIENT_ID.",
        )

    # ── Step 1: Verify the Google ID token ───────────────────────────────────
    try:
        google_payload = id_token.verify_oauth2_token(
            payload.credential,
            GoogleRequest(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        # verify_oauth2_token raises ValueError for expired, tampered,
        # wrong-audience, or malformed tokens.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {exc}",
        )

    # ── Step 2: Extract claims ────────────────────────────────────────────────
    google_id: str = google_payload["sub"]          # stable unique Google user ID
    email: str     = google_payload["email"]
    name: str      = google_payload.get("name", email.split("@")[0])
    # 'name' can be absent on very locked-down Google Workspace accounts;
    # fall back to the local part of the email so StudentProfile.name is
    # never blank.

    # ── Step 3: Upsert User ───────────────────────────────────────────────────
    user = db.query(User).filter(User.google_id == google_id).first()

    if user:
        # Happy path: returning Google user.
        pass

    else:
        email_user = db.query(User).filter(User.email == email).first()

        if email_user:
            # User previously registered with email + password using the same
            # address. Link their Google account so future Google logins work.
            email_user.google_id = google_id
            db.commit()
            db.refresh(email_user)
            user = email_user

        else:
            # First-ever login: create User and StudentProfile together.
            try:
                user = User(
                    email=email,
                    google_id=google_id,
                    hashed_password=None,   # Google-only account; no local password.
                )
                db.add(user)
                db.flush()          # assigns user.id without committing

                student = StudentProfile(
                    user_id=user.id,
                    name=name,
                    email=email,
                    password="",
                )
                db.add(student)
                db.commit()
                db.refresh(user)
                db.refresh(student)
            except Exception:
                db.rollback()
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create account. Please try again.",
                )

    # ── Ensure StudentProfile exists (guard for edge-case orphaned User rows) ──
    student = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not student:
        try:
            student = StudentProfile(user_id=user.id, name=name, email=user.email, password="")
            db.add(student)
            db.commit()
            db.refresh(student)
        except Exception:
            db.rollback()
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create student profile. Please try again.",
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated.",
        )

    # ── Step 4: Issue our JWT ─────────────────────────────────────────────────
    token = create_access_token(user_id=user.id, email=user.email)

    return TokenResponse(
        access_token=token,
        student_id=student.id,
        name=student.name,
        email=user.email,
    )
