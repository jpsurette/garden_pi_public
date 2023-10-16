"""
Saves MQTT subscribed sensor data to influxDB
"""

from dotenv import dotenv_values
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import json



############### MQTT section ##################
# when connecting to mqtt do this;
def on_connect(client, userdata, flags, rc):
    """ The callback for when the client connects to the broker."""
    print("Connected with result code "+str(rc))

    # Subscribe to a topic
    client.subscribe(MQTT_TOPIC)

# when receiving a mqtt message do this;
def on_message(client, userdata, msg):
    """ The callback for when a PUBLISH message is received from the server."""
    sensor_reading = json.loads(msg.payload) # you can use json.loads to convert string to json

    print(sensor_reading)

    #### InfluxDB logic
    write_api.write(bucket=influx_bucket, record=sensor_reading)

MQTT_HOST = "mosquitto"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "soil_readings"

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

# Initiate MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)

write_api = influx_client.write_api(write_options=SYNCHRONOUS)

mqtt_client.loop_forever()




