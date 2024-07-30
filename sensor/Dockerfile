# Build stage
FROM balenalib/raspberry-pi-debian-python:latest

# COPY ./requirements.txt /usr/app/src/requirements.txt

WORKDIR /usr/app/src/

RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools wheel
RUN apt-get update && apt-get -y install build-essential
RUN pip3 install RPi.GPIO --no-binary :all:
RUN pip3 install paho-mqtt
RUN pip3 install pytest-mqtt

#RUN pip3 install -r /usr/app/src/requirements.txt


RUN pip3 install --force-reinstall "adafruit-circuitpython-seesaw==1.15.1"
RUN pip3 install --force-reinstall "Adafruit-Blinka==8.23.0"
RUN pip3 install --force-reinstall "Adafruit-PlatformDetect==3.53.0"

