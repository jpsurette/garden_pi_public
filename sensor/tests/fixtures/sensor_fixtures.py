import json
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# Core mock fixtures
@pytest.fixture
def mock_sensor():
    """Mock sensor fixture with realistic default values"""
    sensor = Mock()
    sensor.get_temp.return_value = 25.0
    sensor.moisture_read.return_value = 45.0
    return sensor

@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client fixture"""
    client = Mock()
    client.loop_start.return_value = None
    client.loop_stop.return_value = None
    client.publish.return_value = None
    return client

# Comprehensive environment fixture
@pytest.fixture
def sensor_test_environment():
    """Complete environment setup for all sensor testing scenarios"""
    with patch('soil_sensor.sensor') as mock_sensor, \
         patch('soil_sensor.mqtt_client') as mock_mqtt_client, \
         patch('soil_sensor.sensor_name', 'test_sensor'), \
         patch('soil_sensor.logging') as mock_logging:
        
        # Setup realistic default values
        mock_sensor.get_temp.return_value = 23.0
        mock_sensor.moisture_read.return_value = 50.0
        
        # Setup MQTT client defaults
        mock_mqtt_client.loop_start.return_value = None
        mock_mqtt_client.loop_stop.return_value = None
        mock_mqtt_client.publish.return_value = None
        
        yield {
            'sensor': mock_sensor,
            'mqtt_client': mock_mqtt_client,
            'logging': mock_logging,
            'sensor_name': 'test_sensor'
        }

# Message validator
@pytest.fixture
def message_validator():
    """Comprehensive message structure validator"""
    def validate_message(message_json, return_error=False):
        """
        Validate the complete structure of a sensor message
        
        Args:
            message_json: JSON string to validate
            return_error: If True, return (False, error_msg) on failure
        """
        try:
            data = json.loads(message_json)
            
            # Validate required structure
            required_fields = ['measurement', 'tags', 'time', 'fields']
            assert all(field in data for field in required_fields), f"Missing required fields: {required_fields}"
            
            # Validate measurement type
            assert data['measurement'] == 'soil_readings', "Invalid measurement type"
            
            # Validate tags structure
            assert 'sensor' in data['tags'], "Missing sensor tag"
            assert isinstance(data['tags']['sensor'], str), "Sensor tag must be string"
            
            # Validate fields structure
            assert 'temp' in data['fields'], "Missing temp field"
            assert 'moisture' in data['fields'], "Missing moisture field"
            
            # Validate field types (can be None or numeric)
            temp = data['fields']['temp']
            moisture = data['fields']['moisture']
            
            if temp is not None:
                assert isinstance(temp, (int, float)), "Temperature must be numeric or None"
            if moisture is not None:
                assert isinstance(moisture, (int, float)), "Moisture must be numeric or None"
            
            # Validate timestamp exists
            assert data['time'] is not None, "Timestamp cannot be None"
            
            return True
            
        except (json.JSONDecodeError, KeyError, AssertionError) as e:
            if return_error:
                return False, str(e)
            return False
    
    return validate_message

# Consolidated test data fixture
@pytest.fixture
def sensor_test_data():
    """Complete test data for sensor readings, MQTT messages, and error scenarios"""
    return {
        'sensor_readings': {
            'normal': {'temp': 23.5, 'moisture': 55.0, 'temp_f': 74.3},
            'extreme_high': {'temp': 45.0, 'moisture': 90.0, 'temp_f': 113.0},
            'extreme_low': {'temp': 0.0, 'moisture': 0.0, 'temp_f': 32.0},
            'negative_temp': {'temp': -10.0, 'moisture': 30.0, 'temp_f': 14.0},
            'precision_test': {
                'temp': 25.456789,
                'moisture': 67.891234,
                'temp_rounded': 25.46,
                'moisture_rounded': 67.89,
                'temp_f': 77.83
            }
        },
        'mqtt_messages': {
            'valid': {
                'measurement': 'soil_readings',
                'tags': {'sensor': 'test_sensor'},
                'time': '2023-07-16T12:00:00Z',
                'fields': {'temp': 75.0, 'moisture': 50.0}
            },
            'null_temp': {
                'measurement': 'soil_readings',
                'tags': {'sensor': 'test_sensor'},
                'time': '2023-07-16T12:00:00Z',
                'fields': {'temp': None, 'moisture': 50.0}
            },
            'null_moisture': {
                'measurement': 'soil_readings',
                'tags': {'sensor': 'test_sensor'},
                'time': '2023-07-16T12:00:00Z',
                'fields': {'temp': 75.0, 'moisture': None}
            },
            'all_null': {
                'measurement': 'soil_readings',
                'tags': {'sensor': 'test_sensor'},
                'time': '2023-07-16T12:00:00Z',
                'fields': {'temp': None, 'moisture': None}
            }
        },
        'mqtt_topics': {
            'production': 'greenhouse/soil/readings',
            'test': 'test/soil/readings',
            'debug': 'debug/soil/readings',
            'sensor_specific': 'sensors/soil_sensor_001/data'
        }
    }

# Failure scenarios fixture
@pytest.fixture
def sensor_failure_scenarios():
    """Comprehensive sensor failure scenarios for testing error handling"""
    return {
        'temp_only_failure': {
            'temp_side_effect': Exception("Temperature sensor offline"),
            'moisture_return': 50.0,
            'expected_temp': None,
            'expected_moisture': 50.0
        },
        'moisture_only_failure': {
            'temp_return': 25.0,
            'moisture_side_effect': Exception("Moisture sensor offline"),
            'expected_temp': 25.0,
            'expected_moisture': None
        },
        'both_sensors_failure': {
            'temp_side_effect': Exception("Hardware failure"),
            'moisture_side_effect': Exception("Hardware failure"),
            'expected_temp': None,
            'expected_moisture': None
        },
        'intermittent_failure': {
            'temp_side_effect': [25.0, Exception("Temporary failure"), 26.0],
            'moisture_return': 45.0
        },
        'mqtt_connection_error': {
            'error_type': 'mqtt',
            'exception': Exception("MQTT broker unreachable"),
            'expected_result': False
        },
        'json_serialization_error': {
            'error_type': 'json',
            'exception': TypeError("Object not JSON serializable"),
            'expected_result': False
        }
    }