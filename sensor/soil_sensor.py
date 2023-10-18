"""
Reads temperature & moisture from soil sensor & publishes to MQTT broker
"""

from datetime import datetime, date
import time as t
import board
from adafruit_seesaw.seesaw import Seesaw
import json
from json import dumps
import socket
from kafka import KafkaProducer

############### sensor inputs ##################

def read_temp():
    # read temperature from the temperature sensor
    temp = round(sensor.get_temp(), 2)
    return temp

def read_moisture():
    # read moisture level through capacitive touch pad
    moisture = round(sensor.moisture_read(), 2)
    return moisture


# for converting datetimes into JSON compatible format
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

# sensor configuration'

i2c_bus = board.I2C()

sensor = Seesaw(i2c_bus, addr=0x36) # check i2cdetect -y 1 for I2c printout & location

sensor_name = socket.gethostname()


# KAFKA configuration

kafka_topic = 'kafkatest'

producer = KafkaProducer(
    bootstrap_servers=['kafka:9094'],
    #security_protocol = 'SSL',
    value_serializer=lambda x: json.dumps(x).encode('utf-8'),
    api_version=(0, 10, 2))


while True:
    
    sensor_reading = {
        'measurement': 'soil_readings',
        'tags': {
            'sensor': sensor_name
        },
        'time': str(datetime.now()),
        'fields': {
            'temp': round(((read_temp() * 1.8) + 32), 2),
            'moisture': read_moisture()
        }
    }

    producer.send(kafka_topic, value=sensor_reading)

    t.sleep(1*30)
