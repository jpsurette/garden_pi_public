# tests/Dockerfile
FROM soil-sensor:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#RUN apt-get update && apt-get install -y 

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app/tests

# will bake-in tests once suite is built out
#COPY ./tests /tests
#COPY ./src /src

#COPY ./tests/pytest.ini /tests/pytest.ini 

COPY requirements.txt .

RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt