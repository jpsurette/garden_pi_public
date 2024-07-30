FROM balenalib/raspberry-pi-debian-python:latest


RUN pip install --upgrade pip
RUN pip install --upgrade setuptools wheel
RUN apt-get update && apt-get -y install build-essential && apt-get install cmake
RUN pip install influxdb_client && pip install python-dotenv && pip install kafka-python && pip install paho-mqtt==1.6.1

RUN pip install pandas==2.2.1
RUN pip install pymongo==4.6.3

WORKDIR /usr/app/src