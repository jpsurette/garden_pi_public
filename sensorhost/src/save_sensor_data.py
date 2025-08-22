"""
Saves MQTT subscribed sensor data to influxDB
"""

import os
import sys
import json
import time
import logging
import random
from datetime import datetime, date
from dotenv import dotenv_values
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from functools import lru_cache


@lru_cache()
def get_influx_config():
    """Caches influx config vars from .env file for testing/production, tests use holder vals for calls from write to DB func"""

    if environment in ("testing", "production"):
        config = dotenv_values(".env")
    else:
        config = {
            'INFLUXDB_BUCKET': os.environ['INFLUXDB_BUCKET'],
            'INFLUXDB_URL': os.environ['INFLUXDB_URL'],
            'INFLUXDB_TOKEN': os.environ['INFLUXDB_TOKEN'],
            'INFLUXDB_ORG': os.environ['INFLUXDB_ORG'],
            'INFLUXDB_USER': os.environ['INFLUXDB_USER'],
            'INFLUXDB_PASSWORD': os.environ['INFLUXDB_PASSWORD']
        }

    return {
            'bucket': config['INFLUXDB_BUCKET'],
            'url': config.get('INFLUXDB_URL'),
            'token': config['INFLUXDB_TOKEN'],
            'org': config['INFLUXDB_ORG'],
            'user': config['INFLUXDB_USER'],
            'password': config['INFLUXDB_PASSWORD']
    }


def on_connect(client, userdata, flags, rc):
    """ The callback for when the client connects to the broker."""
    print("Connected with result code "+str(rc))
    
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    """ The callback for when a PUBLISH message is received from the server."""
    try:
        sensor_reading = json.loads(msg.payload)  # Convert the received payload to JSON
        print(sensor_reading)
        if not circuit_open:
            write_to_influxdb(sensor_reading)
            logging.info(f"Data written to InfluxDB: {sensor_reading}")
    except Exception as e:
        logging.error(f"Failed to write to InfluxDB: {e}")


def write_to_influxdb(sensor_data):
    """Write sensor data to InfluxDB."""
    global circuit_open, failure_count, last_failure_time

    # Initialize InfluxDB client
    influx_config = get_influx_config()

    try:
        with InfluxDBClient(
            url=influx_config['url'],  # Important: include http://
            token=influx_config['token'],
            org=influx_config['org'],
        ) as influx_client:
            write_api = influx_client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=influx_config['bucket'], record=sensor_data)
            failure_count = 0
    except Exception as e:
        print(f"Failed to write to InfluxDB: {e}")
        failure_count += 1
        last_failure_time = time.time()
        if failure_count >= MAX_FAILURES:
            open_circuit()
        raise


def open_circuit():
    """Open the circuit."""
    global circuit_open
    circuit_open = True
    print("Circuit open, waiting for reset timeout...")
    time.sleep(RESET_TIMEOUT)
    circuit_open = False
    print("Circuit closed, attempting to write to InfluxDB again.")
 

def check_health():

    try:
        dummy_sensor_reading = {
            'measurement': 'healthchecks',
            'tags': {'sensor': 'healthcheck'},
            'time': datetime.now(),
            'fields': {
                'temp': round(random.uniform(0, 100), 1),
                'moisture': round(random.uniform(0, 100), 1)
            }
        }

        write_to_influxdb(dummy_sensor_reading)
        logging.info("Healthcheck written to InfluxDB")

        return 0
    
    except Exception as e:
        print("Health check failed: ", str(e))
        return 1


def main():
    # MQTT loop

        mqtt_client.loop_forever()

# Get the value of the ENVIRONMENT variable
environment = os.getenv("ENVIRONMENT")

# Circuit breaker parameters
MAX_FAILURES = 3  # Maximum number of consecutive failures allowed before opening the circuit
RESET_TIMEOUT = 60  # Time in seconds to wait before attempting to reset the circuit after opening

# Circuit breaker state
circuit_open = False
failure_count = 0
last_failure_time = None

############### MQTT section ##################
# MQTT configuration
if environment in [None, "", "production"]:
    MQTT_HOST = "sensorhost"
elif environment == "testing":
    MQTT_HOST = 'sensorhost-test'

MQTT_TOPIC = "soil_readings"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60


# Initialize MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Connect with MQTT Broker
try:
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
    logging.info("Connected to MQTT broker")
except Exception as e:
    logging.error(f"Failed to connect to MQTT broker: {e}")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'check_health':
        sys.exit(check_health())
    else:
        main()