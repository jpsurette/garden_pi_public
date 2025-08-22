# Build stage
FROM balenalib/raspberry-pi-debian-python:3.10
#FROM python:3.12-slim

# COPY ./requirements.txt /usr/app/src/requirements.txt
#RUN apt-get update && apt-get -y install build-essential
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-dev build-essential python3-distutils

# Create a virtualenv WITHOUT system packages
RUN python3 -m venv --without-pip /opt/venv

# Install pip in the venv from source, not system ensurepip
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | /opt/venv/bin/python

# Use venv pip from here on
ENV PATH="/opt/venv/bin:$PATH"

# Install setuptools pinned version, fully isolated
RUN /opt/venv/bin/pip install --no-cache-dir pip==23.0.1 setuptools==57.5.0 wheel==0.38.4
RUN /opt/venv/bin/pip install --no-cache-dir --use-pep517 --no-binary=RPi.GPIO RPi.GPIO==0.7.1
#RUN /opt/venv/bin/pip install --no-cache-dir pip==23.0.1 wheel==0.38.4

#RUN pip3 install --no-binary=RPi.GPIO RPi.GPIO==0.7.1

#RUN pip3 install paho-mqtt
#RUN pip3 install pytest-mqtt
#RUN pip3 install --force-reinstall "adafruit-circuitpython-seesaw==1.15.1"
#RUN pip3 install --force-reinstall "Adafruit-Blinka==8.23.0"
#RUN pip3 install --force-reinstall "Adafruit-PlatformDetect==3.53.0"


# might need gpiozero or lgpio later (07/2025 onward)
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /app/src/

COPY src/ ./
