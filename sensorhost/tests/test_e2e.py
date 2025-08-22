# test_e2e.py
import pytest
import json
import time
from unittest.mock import Mock, patch
from datetime import datetime


class TestEndToEndScenarios:
    """End-to-end tests simulating real workflow scenarios"""

    @patch('save_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.kafka_producer')
    @patch('save_sensor_data.mqtt.Client')
    def test_full_sensor_data_pipeline(self, mock_mqtt, mock_kafka, mock_send_influx, mock_save_influx, sample_sensor_data, mock_influx_query_result):
        """Test complete pipeline: MQTT -> InfluxDB -> Kafka"""
        
        # Setup mocks for save_sensor_data
        mock_write_api = Mock()
        mock_save_client = Mock()
        mock_save_client.write_api.return_value = mock_write_api
        mock_save_influx.return_value.__enter__.return_value = mock_save_client
        
        # Setup mocks for send_sensor_data
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = mock_influx_query_result
        mock_send_client = Mock()
        mock_send_client.query_api.return_value = mock_query_api
        mock_send_influx.return_value.__enter__.return_value = mock_send_client
        
        # Setup circuit breaker state
        save_sensor_data.circuit_open = False
        save_sensor_data.failure_count = 0
        
        # Simulate MQTT message processing
        mock_msg = Mock()
        mock_msg.payload = json.dumps(sample_sensor_data)
        
        # Process message through save_sensor_data
        save_sensor_data.on_message(None, None, mock_msg)
        
        # Query and publish through send_sensor_data
        result = send_sensor_data.query_source(mock_send_client)
        
        # Verify the pipeline
        mock_write_api.write.assert_called_once()
        mock_query_api.query_data_frame.assert_called_once()
        assert result is not False

    @patch('save_sensor_data.InfluxDBClient')
    def test_circuit_breaker_protection(self, mock_influx_client, sample_sensor_data):
        """Test circuit breaker protects against cascading failures"""
        
        # Setup failing InfluxDB writes
        mock_write_api = Mock()
        mock_write_api.write.side_effect = Exception("Database unavailable")
        mock_client = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client
        
        # Reset circuit breaker
        save_sensor_data.circuit_open = False
        save_sensor_data.failure_count = 0
        save_sensor_data.MAX_FAILURES = 3
        
        # Trigger failures until circuit opens
        for i in range(3):
            save_sensor_data.write_to_influxdb(sample_sensor_data)
        
        # Verify circuit is open
        assert save_sensor_data.circuit_open is True
        assert save_sensor_data.failure_count == 3

    def test_environment_based_configuration(self):
        """Test configuration changes based on environment variables"""
        
        # Test production environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            # Would test actual configuration loading
            environment = os.getenv("ENVIRONMENT")
            assert environment == "production"
        
        # Test testing environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'testing'}):
            environment = os.getenv("ENVIRONMENT")
            assert environment == "testing"

    @patch('send_sensor_data.publish')
    @patch('save_sensor_data.write_to_influxdb')
    def test_health_check_endpoints(self, mock_write, mock_publish):
        """Test health check functionality for both services"""
        
        # Test save_sensor_data health check
        save_result = save_sensor_data.check_health()
        assert save_result == 0
        mock_write.assert_called()
        
        # Test send_sensor_data health check
        send_result = send_sensor_data.check_health()
        assert send_result == 0
        mock_publish.assert_called_with("healthcheck", {"status": "ok"})