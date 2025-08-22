"""
Reads temperature & moisture from soil sensor & publishes to MQTT broker
"""

import os
import sys
import logging
import json
import time as t
from datetime import datetime, date
import paho.mqtt.client as mqtt
import board
from adafruit_seesaw.seesaw import Seesaw



############### sensor inputs ##################
def read_temp():
    try:
        temp = round(sensor.get_temp(), 2)
        return temp
    except Exception as e:
        logging.error(f"An error occurred while reading the temperature: {e}")
        return None


def read_moisture():
    try:
        moisture = round(sensor.moisture_read(), 2)
        return moisture
    except Exception as e:
        logging.error(f"An error occurred while reading the moisture: {e}")
        return None


def take_sensor_reading():
    try:
        sensor_reading = {
            'measurement': 'soil_readings',
            'tags': {
                'sensor': sensor_name
            },
            'time': datetime.now(),
            'fields': {
                'temp': round(((read_temp() * 1.8) + 32), 2) if read_temp() is not None else None,
                'moisture': read_moisture()
            }
        }
        return sensor_reading
    except Exception as e:
        logging.error(f"Error taking sensor reading: {e}")
        return None


############### MQTT section ##################
def on_publish(client, userdata, mid):
    try:
        logging.info(f"Published measurement: {MQTT_MSG}")
    except NameError as e:
        logging.error(f"NameError occurred - {MQTT_MSG}")
        logging.error(str(e))
    except Exception as e:
        logging.error(f"Error: {e} - {MQTT_MSG}")
        return False


def on_connect(client, userdata, flags, rc):
    """ The callback for when the client connects to the broker."""
    if rc == 0:
        logging.info("Connected to MQTT broker with result code 0")
    else:
        logging.error(f"Failed to connect to MQTT broker, return code {rc}")


def on_disconnect(client, userdata, flags, rc):
    """ The callback for when the client disconnects from the broker."""
    if rc != 0:
        logging.error("Unexpected disconnection from MQTT broker")


def publish_sensor_reading(mqtt_topic):
    """
    try:
        mqtt_client.loop_start()

        sensor_reading = take_sensor_reading()

        if sensor_reading:
            MQTT_MSG = json.dumps(sensor_reading, default=json_serial)
            mqtt_client.publish(mqtt_topic, MQTT_MSG)
        else:
            logging.warning("Sensor reading returned None, skipping publish")
            return False
        
        mqtt_client.loop_stop()

        return True
    """
    global MQTT_MSG

    try:
        mqtt_client.loop_start()
        sensor_reading = take_sensor_reading()
        
        # Validate sensor reading exists
        if sensor_reading is None:
            logging.warning("Sensor reading returned None, skipping publish")
            mqtt_client.loop_stop()
            return False
            
        # Validate required structure
        if not isinstance(sensor_reading, dict):
            logging.error("Sensor reading is not a valid dictionary, skipping publish")
            mqtt_client.loop_stop()
            return False
            
        # Check for required fields
        if 'fields' not in sensor_reading:
            logging.error("Sensor reading missing 'fields' key, skipping publish")
            mqtt_client.loop_stop()
            return False
            
        fields = sensor_reading['fields']
        if not fields:
            logging.error("Sensor reading 'fields' is empty, skipping publish")
            mqtt_client.loop_stop()
            return False
            
        # Check if all critical measurements are None
        temp = fields.get('temp')
        moisture = fields.get('moisture')
        
        if temp is None and moisture is None:
            logging.error("All sensor measurements are None, skipping publish")
            mqtt_client.loop_stop()
            return False
            
        # Validate data ranges (optional - adjust ranges as needed)
        if temp is not None:
            if not isinstance(temp, (int, float)) or temp < -40 or temp > 150:
                logging.error(f"Temperature reading {temp}°F is invalid or out of range, skipping publish")
                mqtt_client.loop_stop()
                return False
                
        if moisture is not None:
            if not isinstance(moisture, (int, float)) or moisture < 0 or moisture > 1500:
                logging.warning(f"Moisture reading {moisture}% seems invalid or out of range")
                mqtt_client.loop_stop()
                return False

        # Attempt to serialize data
        try:
            MQTT_MSG = json.dumps(sensor_reading, default=json_serial)
        except (TypeError, ValueError) as json_error:
            logging.error(f"Failed to serialize sensor data to JSON: {json_error}")
            mqtt_client.loop_stop()
            return False
            
        # Validate the serialized message isn't empty
        if not MQTT_MSG or MQTT_MSG.strip() == "":
            logging.error("Serialized MQTT message is empty, skipping publish")
            mqtt_client.loop_stop()
            return False
            
        # Attempt to publish
        try:
            result = mqtt_client.publish(mqtt_topic, MQTT_MSG)
            if result.rc != 0:
                logging.error(f"MQTT publish failed with return code: {result.rc}")
                mqtt_client.loop_stop()
                return False
        except Exception as publish_error:
            logging.error(f"Exception during MQTT publish: {publish_error}")
            mqtt_client.loop_stop()
            return False
            
        mqtt_client.loop_stop()
        logging.info("Sensor reading published successfully")
        return True

    except Exception as e:
        logging.error(f"Error during sensor reading and publishing loop: {e}")
        # Ensure loop_stop is called even if there's an exception
        try:
            mqtt_client.loop_stop()
        except Exception as loop_error:
            logging.error(f"Loop stop failed due to {loop_error}")
            pass
        return False


############### Health check function for Docker status ##################
def check_health(max_retries=3, retry_interval=10):
    MQTT_TOPIC = "testing_soil_readings"
    retries = 0
    
    while retries<max_retries:
        if publish_sensor_reading(MQTT_TOPIC):
            logging.info("Health check succeeded")
            return 0
        else:
            retries+=1
            logging.warning(f"Health check failed, retrying in {retry_interval} seconds... (Attempt {retries}/{max_retries})")
            t.sleep(retry_interval)
    
    logging.error("Health check failed after maximum retries")
    return 1


# for converting datetimes into JSON compatible format
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def main():
    if environment in [None, "", "production"]:
        MQTT_TOPIC = "soil_readings"
        logging.info(f"Publishing sensor readings to topic: {MQTT_TOPIC}")
        
    elif environment == "testing":
        MQTT_TOPIC = "soil_readings"
        logging.info(f"Publishing sensor readings to topic: {MQTT_TOPIC} in testing mode")

    # need to add circuit breaker logic
    while True:
            try:
                publish_sensor_reading(MQTT_TOPIC)
            except Exception as e:
                logging.error(f"Error: {e}")
            t.sleep(120)

        
logging.basicConfig(level=logging.DEBUG)

# Get the value of the ENVIRONMENT variable
environment = os.getenv("ENVIRONMENT")
i2c_bus = board.I2C()
sensor = Seesaw(i2c_bus, addr=0x36) # check i2cdetect -y 1 for I2c printout & location
sensor_name = os.getenv("SENSOR_NAME")

# sensor MQTT configuration
if environment in [None, "", "production"]:
    MQTT_HOST = "sensorhost"
elif environment == "testing":
    MQTT_HOST = "sensorhost-test"

logging.info(f"Publishing to : {MQTT_HOST}")
MQTT_PORT = 1883
MQTT_KEEPALIVE_INTERVAL = 120

# Initiate MQTT Client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_publish = on_publish
#mqtt_client.on_disconnect = on_disconnect

# Connect with MQTT Broker
try:
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL)
    logging.info("Connected to MQTT broker")
except Exception as e:
    logging.error(f"Failed to connect to MQTT broker: {e}")
    sys.exit(1)

MQTT_MSG=""


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'check_health':
        exit(check_health())
    else:
        main()





