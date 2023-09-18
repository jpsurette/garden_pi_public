"""
Reads temperature & moisture from soil sensor & publishes to MQTT broker
"""

from datetime import datetime, date
import time as t
import board
from adafruit_seesaw.seesaw import Seesaw
import paho.mqtt.client as mqtt
import json
import socket

############### sensor inputs ##################

def read_temp():
    # read temperature from the temperature sensor
    temp = round(sensor.get_temp(), 2)
    return temp

def read_moisture():
    # read moisture level through capacitive touch pad
    moisture = round(sensor.moisture_read(), 2)
    return moisture


############### MQTT section ##################
def on_publish(client, userdata, mid):
    print(f"Published measurement: {MQTT_MSG}")


def on_connect(client, userdata, flags, rc):
    """ The callback for when the client connects to the broker."""
    print("Connected with result code "+str(rc))


# for converting datetimes into JSON compatible format
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


sensor_name = socket.gethostname()

MQTT_HOST = "sensorhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 60
MQTT_TOPIC = "soil_readings"

i2c_bus = board.I2C()

sensor = Seesaw(i2c_bus, addr=0x36) # check i2cdetect -y 1 for I2c printout & location

# Initiate MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish

# Connect with MQTT Broker
mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
print("connected to MQTT, starting loop")

while True:
    mqtt_client.loop_start()
    
    sensor_reading = {
        'measurement': 'soil_readings',
        'tags': {
            'sensor': sensor_name
        },
        'time': datetime.now(),
        'fields': {
            'temp': round(((read_temp() * 1.8) + 32), 2),
            'moisture': read_moisture()
        }
    }

    MQTT_MSG=json.dumps(sensor_reading, default=json_serial)

    mqtt_client.publish(MQTT_TOPIC, MQTT_MSG)

    mqtt_client.loop_stop()

    t.sleep(1*300)
