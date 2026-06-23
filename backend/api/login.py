# This file is intentionally minimal.
# Login, register, and profile-info are all handled in api/student.py.
# This file is kept only so existing imports in main.py don't break.

from fastapi import APIRouter

router = APIRouter()