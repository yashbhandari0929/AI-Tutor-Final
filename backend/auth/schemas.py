from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Public-safe view of a User. Never includes hashed_password."""
    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student_id: int
    name: str
    email: EmailStr


class TokenPayload(BaseModel):
    """Shape of the JWT 'sub' claim payload once decoded."""
    user_id: int
    email: Optional[EmailStr] = None


# ── Phase 5: Google OAuth ─────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    """
    Payload sent by the frontend after Google Identity Services returns a
    credential. 'credential' is a signed Google ID token (JWT issued by
    Google, NOT our own JWT).
    """
    credential: str