# app/api/auth_routes.py

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import uuid

from app.core.database import get_db_conn, release_db_conn
from app.authentication.security import hash_password, verify_password
from app.authentication.jwt_handler import create_token

router = APIRouter()


# =============================
# REQUEST SCHEMAS
# =============================

class SignupRequest(BaseModel):
    username: str
    password: str
    role: str  # admin / officer / viewer

    full_name: str | None = None
    email: str | None = None
    department: str | None = None
    designation: str | None = None

class LoginRequest(BaseModel):
    username: str
    password: str


# =============================
# SIGNUP
# =============================

@router.post("/signup")
def signup(request: SignupRequest):

    conn = get_db_conn()

    try:
        with conn.cursor() as cur:

            # Check if user exists
            cur.execute("SELECT 1 FROM users WHERE username = %s", (request.username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="User already exists")

            # 🔒 Password validation
            if len(request.password) < 6:
                raise HTTPException(
                    status_code=400,
                    detail="Password must be at least 6 characters"
                )

            # 🔒 Email uniqueness check (only if provided)
            if request.email:
                cur.execute("SELECT 1 FROM users WHERE email = %s", (request.email,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="Email already exists"
                    )

            user_id = str(uuid.uuid4())
            password_hash = hash_password(request.password)
            

            cur.execute("""
                INSERT INTO users (
                    user_id,
                    username,
                    password_hash,
                    role,
                    full_name,
                    email,
                    department,
                    designation
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                request.username,
                password_hash,
                request.role,
                request.full_name,
                request.email,
                request.department,
                request.designation
            ))

            conn.commit()

        return {"message": "User created successfully"}

    finally:
        release_db_conn(conn)


# =============================
# LOGIN
# =============================

@router.post("/login")
def login(request: LoginRequest, req: Request):

    conn = get_db_conn()

    try:
        client_ip = req.client.host if req.client else "unknown"
        with conn.cursor() as cur:

            cur.execute("""
                SELECT user_id, password_hash, role, is_active
                FROM users
                WHERE username = %s
            """, (request.username,))

            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=401, detail="Invalid credentials")

            user_id, password_hash, role, is_active = row
            
            if not is_active:
                raise HTTPException(
                    status_code=403,
                    detail="Account is deactivated"
                )

            if not verify_password(request.password, password_hash):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # 🔥 Update last login timestamp
            cur.execute("""
                UPDATE users
                SET last_login_at = NOW(),
                    last_login_ip = %s
                WHERE user_id = %s
            """, (client_ip, user_id))
            
            conn.commit()

        # 🔐 Generate JWT
        token = create_token({
            "sub": str(user_id),
            "username": request.username   # 🔥 correct source
        })
        
        return {
            "access_token": token,
            "role": role
        }

    finally:
        release_db_conn(conn)