import os
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from musicrec.config import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    CORS_ORIGIN,
    DB_PATH,
    PROCESSED_DIR,
)

from .auth import create_user, issue_token, read_user_id, verify_password
from .catalog import Catalog
from .db import User, open_session


class AuthBody(BaseModel):
    username: str
    password: str


def create_app():
    secret = os.environ.get("MUSICREC_JWT_SECRET")
    if not secret:
        raise RuntimeError("MUSICREC_JWT_SECRET is required")
    db_path = os.environ.get("MUSICREC_DB_PATH", str(DB_PATH))
    processed = Path(os.environ.get("MUSICREC_PROCESSED_DIR", str(PROCESSED_DIR)))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    catalog = Catalog.load(processed)

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[CORS_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def db():
        session = open_session(db_path)
        try:
            yield session
        finally:
            session.close()

    def get_current_user(request: Request, session=Depends(db)):
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            raise HTTPException(status_code=401)
        try:
            user_id = read_user_id(token, secret)
        except jwt.PyJWTError:
            raise HTTPException(status_code=401)
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401)
        return user

    def set_login_cookie(response, user):
        response.set_cookie(
            key=COOKIE_NAME,
            value=issue_token(user.id, secret),
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE,
            max_age=COOKIE_MAX_AGE,
        )

    @app.post("/auth/register")
    def register(body: AuthBody, session=Depends(db)):
        if len(body.password) < 8:
            raise HTTPException(status_code=422, detail="password must be at least 8 characters")
        try:
            create_user(session, body.username, body.password)
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="username already exists")
        return {"username": body.username}

    @app.post("/auth/login")
    def login(body: AuthBody, response: Response, session=Depends(db)):
        user = session.query(User).filter(User.username == body.username).one_or_none()
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401)
        set_login_cookie(response, user)
        return {"username": user.username}

    @app.post("/auth/logout")
    def logout(response: Response):
        response.delete_cookie(COOKIE_NAME)
        return {"ok": True}

    @app.get("/auth/me")
    def me(user=Depends(get_current_user)):
        return {"username": user.username}

    @app.get("/tracks/search")
    def search(q: str = ""):
        return catalog.search(q)

    @app.get("/audio/{track_id}")
    def audio(track_id: int):
        path = catalog.audio_path(track_id)
        if path is None or not Path(path).exists():
            raise HTTPException(status_code=404)
        return FileResponse(path)

    @app.post("/play/{track_id}")
    def play(track_id: int, user=Depends(get_current_user), session=Depends(db)):
        if catalog.audio_path(track_id) is None and track_id not in catalog.by_id:
            raise HTTPException(status_code=404)
        if track_id not in catalog.by_id:
            raise HTTPException(status_code=404)
        catalog.record_play(session, user.id, track_id)
        return {"track": catalog._public(track_id), "neighbors": catalog.content_neighbors(track_id)}

    @app.get("/recommend/history")
    def recommend_history(user=Depends(get_current_user), session=Depends(db)):
        return catalog.recommend(catalog.history_ids(session, user.id))

    return app


app = create_app()
