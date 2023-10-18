# Soil sensor network

Soil readings from a physical sensor to a time series database.

Within seconds of starting the application, or the Pi turns on, sensors will transmit soil readings from the "sensor" application and the "sensorhost" application will store them in a time series database. 

This project is built entirely within Docker containers and can be run off of a single pi (using both sensor and sensorhost containers) or on multiple pis for sensors in various locations. 

An older MQTT-based version offers a parallel setup with lighter weight messaging than Apache Kafka.

## Prequisites

#### Equipment list

- Raspberry Pi running Docker (4b used here)
- [*Adafruit STEMMA Soil Sensor*](https://www.adafruit.com/product/4026)

## Starting
Clone the Git Repository
    
    git clone https://github.com/jpsurette/garden_pi_public.git

Open the file
    
    $/sensorhost/.env 

And replace the hash marks below with your desired credentials.

    INFLUXDB_USER=##########
    INFLUXDB_PASSWORD=###############
    INFLUXDB_TOKEN=###############
    INFLUXDB_URL=http://influxdb:8086
    INFLUXDB_ORG=houseplants
    INFLUXDB_BUCKET=plant_sensors
    GRAFANA_USER=##############
    GRAFANA_PASSWORD=###############

A 32 character token can be generated by running the below within a pi SSH session or on OS X. 

    openssl rand -base64 32

## Running

To start either a sensor or a sensorhost application and their supporting services, navigate to
    
    >$/sensor (to run a sensor)
    
    >$/sensorhost (to run a sensorhost and store your database)

And run

    export HOSTNAME="$(cat /etc/hostname)"

    docker compose up -d

This will save your Pi's hostname to a temporary variable, and that will be used to identify the sensor in influxDB.

The data collected will be available at the endpoint for the influxDB API
[http://influxdb:8086/]



### MQTT Version

The /mqtt_version/ in both the sensor and sensorhost folders uses Mosquitto for MQTT messaging instead of Apache Kafka. Everything else is the same and the data will appear be available in your InfluxDB instance.

Over time this portion will become deprecated.


## In progress updates

##### Short-term
- Grafana visualizations
- HOSTNAME & user name handling

##### Long-term
- Encapsulation of different sensor types