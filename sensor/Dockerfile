# Build stage
FROM balenalib/raspberry-pi-debian-python:latest

#RUN pip install paho-mqtt

RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools wheel
RUN apt-get update && apt-get -y install build-essential
RUN pip3 install RPi.GPIO --no-binary :all:
RUN pip3 install adafruit-circuitpython-seesaw
RUN pip3 install Adafruit-Blinka
RUN pip3 install paho-mqtt

WORKDIR /usr/app/src

# Copy the Python script & reqs to the container
#COPY soil_sensor.py ./
#COPY ./requirements.txt /app/requirements.txt

