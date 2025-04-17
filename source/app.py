from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from prometheus_client import start_http_server, Counter, Histogram
import time

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

@app.on_event("startup")
def startup_prometheus():
    start_http_server(9000)

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Общее число HTTP‑запросов',
    ['method', 'endpoint', 'http_status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'Время обработки HTTP‑запроса в секундах',
    ['method', 'endpoint']
)

@app.middleware("http")
async def prometheus_http_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(method, endpoint).observe(duration)
    return response

