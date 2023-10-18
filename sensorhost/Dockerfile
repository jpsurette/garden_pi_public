FROM balenalib/raspberry-pi-debian-python:latest

RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools wheel
RUN apt-get update && apt-get -y install build-essential
RUN pip3 install influxdb_client
RUN pip3 install python-dotenv
RUN pip3 install kafka-python

WORKDIR /usr/app/src


