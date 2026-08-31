from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db, init_db, User
from auth import verify_password, get_password_hash, create_access_token, get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterIn(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register", status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already registered")

    user = User(username=body.username, hashed_password=get_password_hash(body.password))
    db.add(user)
    await db.commit()
    return {"id": user.id, "username": user.username}


@app.post("/api/auth/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token({"sub": user.username}),
        "token_type": "bearer",
    }


@app.get("/api/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "is_active": user.is_active}