# Soil sensor network

Each sensor publishes an MQTT message containing soil temperature and moisture measurements taken via attached soil sensors. Sensorhost receives measurements from a scalable array of sensors and stores the data in an influxDB instance. Within seconds of startup, sensors will begin to transmit readings and the sensorhost will store them in a time series database. This project is built entirely within Docker containers.

### Equipment list

- Raspberry Pi 
- Adafruit STEMMA Soil Sensor (*From https://www.adafruit.com/product/4026*)


#### Populate a .env file in your /sensorhost/ directory with fields
    INFLUXDB_USER=user
    INFLUXDB_PASSWORD=###############
    INFLUXDB_TOKEN=###############
    INFLUXDB_URL=http://influxdb:8086
    INFLUXDB_ORG=houseplants
    INFLUXDB_BUCKET=plant_sensors
