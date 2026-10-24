from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from musicrec.config import COOKIE_MAX_AGE

from .db import User


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_user(session, username, password):
    user = User(
        username=username,
        password_hash=hash_password(password),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def issue_token(user_id, secret):
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=COOKIE_MAX_AGE),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def read_user_id(token, secret):
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return int(payload["sub"])
