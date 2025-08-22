# tests/Dockerfile
FROM soil-sensorhost:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY tests/requirements-testing.txt /app/tests/

WORKDIR /app/tests

RUN apt-get update && apt-get install -y \
    libpq-dev \
    postgresql-client \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements-testing.txt