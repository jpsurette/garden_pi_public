FROM balenalib/raspberry-pi-debian-python:3.10

WORKDIR /app/src

RUN pip install --upgrade pip==24.3.1 setuptools==75.6.0 wheel && \
    apt-get update && apt-get -y install build-essential cmake

COPY requirements-sensorhost.txt .

RUN pip install -r requirements-sensorhost.txt


