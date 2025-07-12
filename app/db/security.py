import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from starlette.status import HTTP_401_UNAUTHORIZED

from app.db.container import Container
from app.db.factory import Database
from app.db.models import User

logger = logging.getLogger(__name__)


SECRET_KEY = os.getenv("CMDA_AUTH_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict[str, Any]) -> str:
    """
    Create encoded JWT with user data
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@inject
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Database = Depends(Provide[Container.database]),
) -> User:
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        raise credentials_exception

    # Grab username data and try and grab user
    username: str = payload.get("username")
    if username is None:
        raise credentials_exception
    user = db.get_object(
        db_type=User,
        where_conditions={"username": username},
        headers={"WWW-Authenticate": "Bearer"},
    )
    return user
