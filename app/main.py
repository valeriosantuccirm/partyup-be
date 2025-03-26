import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlmodel import SQLModel
from starlette.middleware.sessions import SessionMiddleware

from app.api.routers import auth, events, maps, public_users, user, user_events, user_hivers
from app.database.crud.elasticsearch.esclient import ElasticsearchMeta
from app.database.redis import redis_client
from app.database.session import engine


# create tables from models
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, Any]:
    """Handles database and Redis initialization."""

    # 🚀 1️ Setup Database
    async with engine.begin() as conn:
        await conn.run_sync(fn=SQLModel.metadata.create_all)

    # 🚀 2️ Connect to Redis
    print("🔗 Connecting to Redis...")
    await redis_client.connect()

    # 🚀 3 Connect to Elasticsearch
    print("🔗 Connecting to Elasticsearch...")
    await ElasticsearchMeta.init_client()

    yield  # App runs during this phase

    # 🚀 4 Cleanup Redis and Elasticsearch
    print("🔴 Disconnecting from Redis and Elasticsearch...")
    await redis_client.disconnect()
    await ElasticsearchMeta.close_client()


# instanciate app
app: FastAPI = FastAPI(
    title="Partu Up",
    description="Partu Up - App to create events and share them with the community!",
    version="1",
    contact={
        "name": "Valerio Santucci",
        "email": "valerio.santucci.rm@gmail.com",
    },
    lifespan=lifespan,
)

# ensure secure client-side session
app.add_middleware(
    middleware_class=SessionMiddleware,
    secret_key=os.environ.get(
        "SESSION_MIDDLEWARE_SECRET_KEY",
        default="SESSION_MIDDLEWARE_SECRET_KEY",
    ),
)
# compress response to limit bandwith
app.add_middleware(middleware_class=GZipMiddleware)


# allow comunication with frontend if in different origins
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# include routers
app.include_router(router=auth.router, tags=["Auth"])
app.include_router(router=user.router, tags=["User"])
app.include_router(router=user_events.router, tags=["User Events"])
app.include_router(router=events.router, tags=["Events"])
app.include_router(router=public_users.router, tags=["Public Users"])
app.include_router(router=user_hivers.router, tags=["User Hivers"])
app.include_router(router=maps.router, tags=["Maps"])
# app.include_router(router=events_streams.wsrouter, tags=["Events Streams WebSocket"]) #TODO: feature to implement

# add monitoring metrics source
Instrumentator().instrument(app=app).expose(app=app)

if __name__ == "__main__":
    uvicorn.run(app="app.main:app", reload=True, host="0.0.0.0", port=8000)
