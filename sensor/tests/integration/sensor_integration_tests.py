# tests/integration/test_soil_sensor_integration.py
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.mark.integration
class TestSensorToDataIntegration:
    """Integration tests for sensor reading to data processing workflow"""
    
    @patch('soil_sensor.sensor')
    @patch('soil_sensor.sensor_name', 'integration_sensor')
    def test_sensor_reading_to_data_structure(self, mock_sensor):
        """Test complete sensor reading to structured data workflow"""
        mock_sensor.get_temp.return_value = 20.0
        mock_sensor.moisture_read.return_value = 50.0
        
        from soil_sensor import take_sensor_reading
        
        result = take_sensor_reading()
        
        # Verify complete data structure
        assert result['measurement'] == 'soil_readings'
        assert result['tags']['sensor'] == 'integration_sensor'
        assert result['fields']['temp'] == 68.0  # (20 * 1.8) + 32
        assert result['fields']['moisture'] == 50.0
        assert isinstance(result['time'], datetime)
    
    @patch('soil_sensor.sensor')
    @patch('soil_sensor.sensor_name', 'integration_sensor')
    def test_partial_sensor_failure_handling(self, mock_sensor):
        """Test workflow continues with partial sensor failures"""
        mock_sensor.get_temp.side_effect = Exception("Temperature sensor failure")
        mock_sensor.moisture_read.return_value = 50.0
        
        from soil_sensor import take_sensor_reading
        
        result = take_sensor_reading()
        
        # Should still produce valid structure with available data
        assert result is not None
        assert result['fields']['temp'] is None
        assert result['fields']['moisture'] == 50.0
        assert result['measurement'] == 'soil_readings'
    
    @patch('soil_sensor.sensor')
    def test_precision_maintained_through_workflow(self, mock_sensor):
        """Test precision is maintained from sensor to final data"""
        mock_sensor.get_temp.return_value = 25.6789  # Should round to 25.68
        mock_sensor.moisture_read.return_value = 45.1234  # Should round to 45.12
        
        with patch('soil_sensor.sensor_name', 'precision_sensor'):
            from soil_sensor import take_sensor_reading
            
            result = take_sensor_reading()
            
            # Temperature: 25.68°C * 1.8 + 32 = 78.22°F
            expected_temp_f = round(((25.68 * 1.8) + 32), 2)
            
            assert result['fields']['temp'] == expected_temp_f
            assert result['fields']['moisture'] == 45.12


@pytest.mark.integration
class TestMQTTPublishIntegration:
    """Integration tests for MQTT publishing workflow"""
    
    @patch('soil_sensor.mqtt_client')
    @patch('soil_sensor.take_sensor_reading')
    @patch('soil_sensor.json')
    def test_data_to_mqtt_publish_workflow(self, mock_json, mock_take_reading, mock_client):
        """Test data processing to MQTT publishing workflow"""
        mock_sensor_data = {
            'measurement': 'soil_readings',
            'tags': {'sensor': 'test_sensor'},
            'time': datetime.now(),
            'fields': {'temp': 77.0, 'moisture': 45.0}
        }
        
        mock_take_reading.return_value = mock_sensor_data
        mock_json.dumps.return_value = '{"test": "data"}'
        
        mock_publish_result = MagicMock()
        mock_publish_result.rc = 0
        mock_client.publish.return_value = mock_publish_result
        
        from soil_sensor import publish_sensor_reading
        result = publish_sensor_reading('test/topic')
        
        assert result is True
        mock_client.loop_start.assert_called_once()
        mock_client.publish.assert_called_once_with('test/topic', '{"test": "data"}')
        mock_client.loop_stop.assert_called_once()
    
    @patch('soil_sensor.mqtt_client')
    @patch('soil_sensor.take_sensor_reading')
    @patch('soil_sensor.logging')
    def test_publish_handles_no_sensor_data(self, mock_logging, mock_take_reading, mock_client):
        """Test publish workflow handles missing sensor data gracefully"""
        mock_take_reading.return_value = None
        
        from soil_sensor import publish_sensor_reading
        result = publish_sensor_reading('test/topic')
        
        assert result is False
        mock_client.loop_start.assert_called_once()
        mock_client.publish.assert_not_called()
        mock_logging.warning.assert_called_once_with("Sensor reading returned None, skipping publish")
    
    @patch('soil_sensor.mqtt_client')
    @patch('soil_sensor.take_sensor_reading')
    @patch('soil_sensor.logging')
    def test_publish_handles_json_serialization_error(self, mock_logging, mock_take_reading, mock_client):
        """Test publish workflow handles JSON serialization errors"""
        mock_sensor_data = {
            'measurement': 'soil_readings',
            'tags': {'sensor': 'test_sensor'},
            'time': datetime.now(),
            'fields': {'temp': 77.0, 'moisture': 45.0}
        }
        mock_take_reading.return_value = mock_sensor_data
        
        with patch('soil_sensor.json.dumps', side_effect=TypeError("Object not serializable")):
            from soil_sensor import publish_sensor_reading
            
            result = publish_sensor_reading('test/topic')
            
            assert result is False
            mock_logging.error.assert_called()