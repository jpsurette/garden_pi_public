# tests/unit/test_soil_sensor.py
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.mark.unit
class TestSensorReading:
    """Unit tests for individual sensor reading functions"""
    
    @patch('soil_sensor.sensor')
    @patch('soil_sensor.logging')
    def test_read_temp_success(self, mock_logging, mock_sensor):
        """Test successful temperature reading with proper rounding"""
        mock_sensor.get_temp.return_value = 25.678
        
        from soil_sensor import read_temp
        result = read_temp()
        
        assert result == 25.68
        mock_sensor.get_temp.assert_called_once()
        mock_logging.error.assert_not_called()
    
    @patch('soil_sensor.sensor')
    @patch('soil_sensor.logging')
    def test_read_temp_exception(self, mock_logging, mock_sensor):
        """Test temperature reading handles sensor exceptions"""
        mock_sensor.get_temp.side_effect = Exception("Sensor error")
        
        from soil_sensor import read_temp
        result = read_temp()
        
        assert result is None
        mock_logging.error.assert_called_once()
    
    @patch('soil_sensor.sensor')
    @patch('soil_sensor.logging')
    def test_read_moisture_success(self, mock_logging, mock_sensor):
        """Test successful moisture reading with proper rounding"""
        mock_sensor.moisture_read.return_value = 45.123
        
        from soil_sensor import read_moisture
        result = read_moisture()
        
        assert result == 45.12
        mock_sensor.moisture_read.assert_called_once()
        mock_logging.error.assert_not_called()
    
    @patch('soil_sensor.sensor')
    @patch('soil_sensor.logging')
    def test_read_moisture_exception(self, mock_logging, mock_sensor):
        """Test moisture reading handles sensor exceptions"""
        mock_sensor.moisture_read.side_effect = Exception("Moisture sensor error")
        
        from soil_sensor import read_moisture
        result = read_moisture()
        
        assert result is None
        mock_logging.error.assert_called_once()


@pytest.mark.unit
class TestSensorDataProcessing:
    """Unit tests for sensor data processing and conversion"""
    
    @patch('soil_sensor.read_temp')
    @patch('soil_sensor.read_moisture')
    @patch('soil_sensor.sensor_name', 'test_sensor')
    def test_take_sensor_reading_success(self, mock_moisture, mock_temp):
        """Test successful sensor data collection and Celsius to Fahrenheit conversion"""
        mock_temp.return_value = 25.0
        mock_moisture.return_value = 45.0
        
        from soil_sensor import take_sensor_reading
        result = take_sensor_reading()
        
        assert result is not None
        assert result['measurement'] == 'soil_readings'
        assert result['tags']['sensor'] == 'test_sensor'
        assert result['fields']['temp'] == 77.0  # (25 * 1.8) + 32
        assert result['fields']['moisture'] == 45.0
        assert isinstance(result['time'], datetime)
    
    @patch('soil_sensor.read_temp')
    @patch('soil_sensor.read_moisture')
    @patch('soil_sensor.sensor_name', 'test_sensor')
    def test_take_sensor_reading_with_none_values(self, mock_moisture, mock_temp):
        """Test sensor reading handles None values from failed sensors"""
        mock_temp.return_value = None
        mock_moisture.return_value = 45.0
        
        from soil_sensor import take_sensor_reading
        result = take_sensor_reading()
        
        assert result is not None
        assert result['fields']['temp'] is None
        assert result['fields']['moisture'] == 45.0
    
    @patch('soil_sensor.read_temp')
    @patch('soil_sensor.read_moisture')
    @patch('soil_sensor.logging')
    def test_take_sensor_reading_exception(self, mock_logging, mock_moisture, mock_temp):
        """Test sensor reading handles unexpected exceptions"""
        mock_temp.side_effect = Exception("Unexpected error")
        
        from soil_sensor import take_sensor_reading
        result = take_sensor_reading()
        
        assert result is None
        mock_logging.error.assert_called_once()
    
    def test_temperature_conversion_boundary_values(self):
        """Test temperature conversion with boundary values"""
        from soil_sensor import take_sensor_reading
        
        test_cases = [
            (0.0, 32.0),      # Freezing point
            (100.0, 212.0),   # Boiling point
            (-10.0, 14.0),    # Negative temperature
        ]
        
        for celsius, expected_fahrenheit in test_cases:
            with patch('soil_sensor.read_temp', return_value=celsius), \
                 patch('soil_sensor.read_moisture', return_value=50.0), \
                 patch('soil_sensor.sensor_name', 'test_sensor'):
                
                result = take_sensor_reading()
                assert result['fields']['temp'] == expected_fahrenheit


@pytest.mark.unit
class TestMQTTCallbacks:
    """Unit tests for MQTT callback functions"""
    
    @patch('soil_sensor.logging')
    @patch('soil_sensor.MQTT_MSG', 'test_message')
    def test_on_publish_success(self, mock_logging):
        """Test MQTT publish callback logs successful publication"""
        from soil_sensor import on_publish
        
        client = Mock()
        userdata = Mock()
        mid = 123
        
        on_publish(client, userdata, mid)
        
        mock_logging.info.assert_called_once_with("Published measurement: test_message")
    
    @patch('soil_sensor.logging')
    def test_on_connect_success(self, mock_logging):
        """Test MQTT connection callback handles successful connection"""
        from soil_sensor import on_connect
        
        on_connect(Mock(), Mock(), Mock(), 0)
        
        mock_logging.info.assert_called_once_with("Connected to MQTT broker with result code 0")
    
    @patch('soil_sensor.logging')
    def test_on_connect_failure(self, mock_logging):
        """Test MQTT connection callback handles connection failure"""
        from soil_sensor import on_connect
        
        on_connect(Mock(), Mock(), Mock(), 1)
        
        mock_logging.error.assert_called_once_with("Failed to connect to MQTT broker, return code 1")
    
    @patch('soil_sensor.logging')
    def test_on_disconnect_unexpected(self, mock_logging):
        """Test MQTT disconnect callback handles unexpected disconnection"""
        from soil_sensor import on_disconnect
        
        on_disconnect(Mock(), Mock(), Mock(), 1)
        
        mock_logging.error.assert_called_once_with("Unexpected disconnection from MQTT broker")
    
    @patch('soil_sensor.logging')
    def test_on_disconnect_expected(self, mock_logging):
        """Test MQTT disconnect callback ignores expected disconnection"""
        from soil_sensor import on_disconnect
        
        on_disconnect(Mock(), Mock(), Mock(), 0)
        
        mock_logging.error.assert_not_called()