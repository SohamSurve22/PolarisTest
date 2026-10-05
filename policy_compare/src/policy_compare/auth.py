"""Login / register routes backed by MongoDB (collection: polarislex.users)."""

from __future__ import annotations

import datetime as dt
import os

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

router = APIRouter(prefix="/auth", tags=["auth"])

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me")
ROLES = {"user", "officer"}
# Officers must use an official government email domain (comma-separated, env-overridable).
GOVT_DOMAINS = [
  d.strip().lower()
  for d in os.environ.get("GOVT_EMAIL_DOMAINS", "gov.in,nic.in").split(",")
  if d.strip()
]


def is_govt_email(email: str) -> bool:
  domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
  return any(domain == d or domain.endswith("." + d) for d in GOVT_DOMAINS)

_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
users = _client["polarislex"]["users"]
_index_ready = False


def _ensure_index() -> None:
  global _index_ready
  if not _index_ready:
    users.create_index("email", unique=True)
    _index_ready = True


class Creds(BaseModel):
  email: str
  password: str
  role: str = "user"  # "user" | "officer"


def _token(user: dict) -> str:
  exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=8)
  return jwt.encode({"sub": user["email"], "role": user["role"], "exp": exp}, JWT_SECRET, "HS256")


@router.post("/register")
def register(c: Creds):
  """Citizens only. Officer accounts are created with scripts/seed_users.py."""
  email = c.email.strip().lower()
  if len(c.password) < 6:
    raise HTTPException(400, "Password must be at least 6 characters")
  hashed = bcrypt.hashpw(c.password.encode(), bcrypt.gensalt())
  try:
    _ensure_index()
    users.insert_one(
      {
        "email": email,
        "passwordHash": hashed,
        "role": "user",
        "createdAt": dt.datetime.now(dt.timezone.utc),
      }
    )
  except DuplicateKeyError:
    raise HTTPException(409, "Email already registered") from None
  except PyMongoError:
    raise HTTPException(503, "Database unavailable") from None
  return {"ok": True}


@router.post("/login")
def login(c: Creds):
  if c.role not in ROLES:
    raise HTTPException(400, "Invalid role")
  email = c.email.strip().lower()
  if c.role == "officer" and not is_govt_email(email):
    raise HTTPException(403, "Officers must use an official government email (gov.in or nic.in)")
  try:
    user = users.find_one({"email": email, "role": c.role})
  except PyMongoError:
    raise HTTPException(503, "Database unavailable") from None
  if not user or not bcrypt.checkpw(c.password.encode(), user["passwordHash"]):
    raise HTTPException(401, "Invalid email or password")
  return {"token": _token(user), "role": user["role"]}
