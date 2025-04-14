from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from source.constants import APIINFO
from source.routers import __all__ as routers


def get_application():
    # app = FastAPI(lifespan=lifespan, title=APIINFO.title, version=APIINFO.version)
    app = FastAPI(title=APIINFO.title,
                  version=APIINFO.version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in routers:
        app.include_router(router)

    return app


app = get_application()
