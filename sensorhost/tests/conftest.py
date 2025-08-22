# conftest.py
import pytest
import os
import json
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


def pytest_sessionstart(session):
    """Sets env vars at runtime (before test import)"""
    os.environ['INFLUXDB_BUCKET'] = 'test_bucket'
    os.environ['INFLUXDB_URL'] = 'http://localhost:8086'
    os.environ['INFLUXDB_TOKEN'] = 'test_token'
    os.environ['INFLUXDB_ORG'] = 'test_org'
    os.environ['INFLUXDB_USER'] = 'test_user'
    os.environ['INFLUXDB_PASSWORD'] = 'test_password'


@pytest.fixture
def sample_sensor_data():
    """Sample sensor data for testing."""
    return {
        'measurement': 'soil_readings',
        'tags': {'sensor': 'test_sensor'},
        'time': datetime.now(),
        'fields': {
            'temp': 25.5,
            'moisture': 65.2
        }
    }


@pytest.fixture
def sample_mqtt_message():
    """Sample MQTT message payload."""
    return json.dumps({
        'measurement': 'soil_readings',
        'tags': {'sensor': 'test_sensor'},
        'time': '2024-01-01T12:00:00Z',
        'fields': {
            'temp': 25.5,
            'moisture': 65.2
        }
    })


@pytest.fixture
def mock_influx_query_result():
    """Mock InfluxDB query result as DataFrame."""
    data = {
        '_time': [datetime.now()],
        'temp': [25.5],
        'moisture': [65.2],
        'result': ['_result'],
        'table': [0],
        '_start': [datetime.now()],
        '_stop': [datetime.now()],
        '_measurement': ['soil_readings']
    }
    return pd.DataFrame(data)