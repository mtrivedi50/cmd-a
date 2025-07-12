import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from starlette.middleware.sessions import SessionMiddleware

from app.db.container import Container

# For enabling authentication via Swagger docs
from app.db.security import *  # type: ignore # noqa: F403
from app.rest_api.auth import router as user_router
from app.rest_api.chat import router as chat_router
from app.rest_api.chat_models import router as chat_models_router
from app.rest_api.integrations import router as integrations_router
from app.rest_api.k8s import router as k8s_router
from app.settings import Settings

# from fastapi.staticfiles import StaticFiles


container = Container()
container.init_resources()

app = FastAPI()
app.container = container
app.include_router(user_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(chat_models_router, prefix="/api/v1")
app.include_router(k8s_router, prefix="/api/v1")
add_pagination(app)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=[Settings.CLIENT_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_MIDDLEWARE_SECRET_KEY", "test"),
    max_age=None,  # session cookies expire when the browser is closed
)

# Static / templates
# app.mount("/assets", StaticFiles(directory="client/dist/assets"), name="assets")
