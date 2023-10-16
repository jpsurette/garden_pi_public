"""
Saves Kafka messaged sensor data to influxDB
"""

from dotenv import dotenv_values
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import json
from time import sleep
from json import loads
from kafka import KafkaConsumer
import threading
import logging

# KAFKA
consumer = KafkaConsumer(
    'kafkatest',
    bootstrap_servers=['kafka:9094'],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    api_version=(0, 10, 2))


"""
Initialize influxDB client
"""
influx_config = dotenv_values(".env")

influx_bucket = influx_config['INFLUXDB_BUCKET']
influx_url = influx_config['INFLUXDB_URL']
influx_token = influx_config['INFLUXDB_TOKEN'] 
influx_org = influx_config['INFLUXDB_ORG']
influx_user = influx_config['INFLUXDB_USER']
influx_password = influx_config['INFLUXDB_PASSWORD']

influx_client = InfluxDBClient(url=influx_url, port=8086, username=influx_user, password=influx_password, token=influx_token, org=influx_org)

write_api = influx_client.write_api(write_options=SYNCHRONOUS)

for reading in consumer:
    sensor_reading = reading.value
    write_api.write(bucket=influx_bucket, record=sensor_reading)









