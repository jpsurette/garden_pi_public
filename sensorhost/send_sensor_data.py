"""
Publishes sensor data from influxDB to Kafka topic
"""

import os
import json
from datetime import datetime, timedelta
import time
import random
import pandas as pd
from kafka import KafkaProducer
from influxdb_client import InfluxDBClient
from dotenv import dotenv_values
import logging
import pymongo
import sys


# Function to query InfluxDB
def query_source(influx_client):
   
        try:
            
                query = '''
                    from(bucket:"plant_sensors") 
                    |> range(start: -5m) 
                    |> filter(fn: (r) => r["_measurement"] == "soil_readings")
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    '''

                results = influx_client.query_api().query_data_frame(query)

                # Check if the results are a list (indicating an empty or malformed result set)
                if isinstance(results, list):
                    if not results:
                        logging.warning("Query returned an empty list.")
                        return False    
    
                # Clean up the DataFrame by dropping unnecessary columns
                results = results.drop(columns=['result', 'table', '_start', '_stop', '_measurement'], errors='ignore')
                results.rename(columns={'_time': 'time'}, inplace=True)
    
                # Convert DataFrame to JSON for further processing
                results_json = results.to_json(orient='records', lines=True)

                #logging.info(results_json)
                return results_json

        except Exception as e:
            logging.error("An error occurred: %s", str(e))
            return False


##@retry(stop_max_attempt_number=3, wait_fixed=2000) # need to implement retrying in dockerfile
def connect_kafka_producer():

    global kafka_topic

    # KAFKA configuration       
    if environment is None or environment in ["","production"]:
        # Production mode logic
        kafka_topic = 'sensordata'
        kafka_server = 'kafka_production:9092'
    elif environment == "testing":
        # Testing mode logic
        kafka_topic = 'sensordata'
        kafka_server = 'kafka_testing:9092'
    else:
        raise ValueError("Unknown environment specified")


    return KafkaProducer(
        bootstrap_servers=[kafka_server],
        #security_protocol = 'SSL',
        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
        api_version=(0, 10, 2),
        request_timeout_ms=120000,
        retries=5,
        retry_backoff_ms=1000,
        batch_size=16384,
        linger_ms=10
    )


def publish(topic, message, max_retries=3, retry_delay=1):

    attempt = 0
    while attempt < max_retries:
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
                
            for line in message.split('\n'):
                if not line.strip():
                    continue
                record = json.loads(line)
                kafka_producer.send(topic, value=record)
            logging.info(f"Messages sent to topic '{topic}'")
        except Exception as e:
            logging.error(f"Error sending messages to Kafka: {str(e)}")
            raise

        attempt += 1
        time.sleep(retry_delay)

#        # Update last query time to the end time of the current query
#        end_time = datetime.now()
#        latest_timestamp = end_time
#
#        return latest_timestamp
#
    logging.error(f"Failed to send message to Kafka after {max_retries} retries")


def check_health():
    
    try:
        health_message = {"status":"ok"}
        publish("healthcheck", health_message)
        logging.info("Health check successful")
        return 0
    except Exception as e:
        logging.error("Health check failed: %s", str(e))
        return 1


def main():
    while True: 
        
        try:
            with InfluxDBClient(url=influx_url, port=8086, token=influx_token, org=influx_org) as influx_client:
                json_results = query_source(influx_client)
                logging.info(json_results)

            publish(kafka_topic, json_results)

            time.sleep(300)

        except Exception as e:
            logging.error("An error occurred: %s", str(e))
            return False


logging.basicConfig(level=logging.INFO) #DEBUG for problem code

# Get the value of the ENVIRONMENT variable
environment = os.getenv("ENVIRONMENT")

kafka_producer = connect_kafka_producer()

"""
Initialize influxDB client
"""
influx_config = dotenv_values(".env")

influx_bucket = influx_config['INFLUXDB_BUCKET']
influx_url = influx_config['INFLUXDB_URL'] # testing vs production urls in .env file
influx_token = influx_config['INFLUXDB_TOKEN']
influx_org = influx_config['INFLUXDB_ORG']
influx_user = influx_config['INFLUXDB_USER']
influx_password = influx_config['INFLUXDB_PASSWORD']

latest_source_timestamp = None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'check_health':
        check_health()
    else:
        logging.info('starting main loop')
        main()




## Function to connect to MongoDB and retrieve the latest timestamp
## mongoDB not yet implemented
#def get_latest_timestamp_from_destination():
#    try:
#        # Establish connection to MongoDB
#        client = pymongo.MongoClient("mongodb://localhost:27017/")
#        
#        # Select database
#        db = client["mydatabase"]
#
#        # Select collection
#        collection = db["timestamps"]
#
#        # Query documents and retrieve the latest timestamp
#        latest_timestamp = collection.find_one({}, sort=[('_id', pymongo.DESCENDING)])  # Assuming timestamps are stored in a collection named 'timestamps'
#        return latest_timestamp['timestamp'] if latest_timestamp else None
#    except Exception as e:
#        #logging.error("Error connecting to MongoDB: %s", str(e))
#        return None
#
#
#def get_latest_timestamp_from_source(latest_timestamp):
#    #global latest_timestamp
#    # Adjust the query based on the latest timestamp from MongoDB, if available
#    if latest_timestamp:
#        start_time = latest_timestamp
#    else:
#        start_time = datetime.now().date() - timedelta(days=10)

