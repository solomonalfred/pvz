FROM python:3.12-slim

WORKDIR /

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD alembic upgrade head && uvicorn source.app:app --host 0.0.0.0 --port ${PORT}
