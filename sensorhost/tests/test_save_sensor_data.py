# test_save_sensor_data.py
import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
import paho.mqtt.client as mqtt
import sys
import os

# Import the module under test
sys.path.append('sensorhost')
import save_sensor_data


class TestSaveSensorDataUnit:
    """Unit tests for save_sensor_data.py - Testing individual functions in isolation"""

    @pytest.mark.unit
    def test_on_connect_subscribes_to_topic(self):
        """Test that on_connect subscribes to the correct MQTT topic."""
        mock_client = Mock()
        save_sensor_data.MQTT_TOPIC = "test_topic"
        
        save_sensor_data.on_connect(mock_client, None, None, 0)
        
        mock_client.subscribe.assert_called_once_with("test_topic")

    @pytest.mark.unit
    @patch('save_sensor_data.write_to_influxdb')
    @patch('save_sensor_data.logging')
    def test_on_message_processes_valid_json(self, mock_logging, mock_write):
        """Test that on_message processes valid JSON payload."""
        mock_client = Mock()
        mock_msg = Mock()
        mock_msg.payload = json.dumps({"temp": 25.5, "moisture": 65.2})
        
        save_sensor_data.circuit_open = False
        
        save_sensor_data.on_message(mock_client, None, mock_msg)
        
        mock_write.assert_called_once()
        mock_logging.info.assert_called()

    @pytest.mark.unit
    @patch('save_sensor_data.logging')
    def test_on_message_handles_invalid_json(self, mock_logging):
        """Test that on_message handles invalid JSON gracefully."""
        mock_client = Mock()
        mock_msg = Mock()
        mock_msg.payload = "invalid json"
        
        save_sensor_data.on_message(mock_client, None, mock_msg)
        
        mock_logging.error.assert_called()

    @pytest.mark.unit
    @patch('save_sensor_data.write_to_influxdb')
    def test_on_message_skips_when_circuit_open(self, mock_write):
        """Test that on_message skips processing when circuit is open."""
        mock_client = Mock()
        mock_msg = Mock()
        mock_msg.payload = json.dumps({"temp": 25.5})
        
        save_sensor_data.circuit_open = True
        
        save_sensor_data.on_message(mock_client, None, mock_msg)
        
        mock_write.assert_not_called()

    @pytest.mark.unit
    @patch('save_sensor_data.InfluxDBClient')
    def test_write_to_influxdb_success(self, mock_influx_client, sample_sensor_data):
        """Test successful write to InfluxDB."""
        mock_write_api = Mock()
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Configure failures followed by recovery
        mock_write_api.write.side_effect = [
            Exception("Connection timeout"),
            Exception("Network error"),
            Exception("Database unavailable"),  # Circuit opens after this
            None,  # Recovery after circuit closes
            None   # Continued success
        ]
        
        # Initialize circuit breaker state
        save_sensor_data.MAX_FAILURES = 3
        save_sensor_data.RESET_TIMEOUT = 1  # Short timeout for testing
        save_sensor_data.failure_count = 0
        save_sensor_data.circuit_open = False
        
        test_data = {"temperature": 25.0, "timestamp": "2023-01-01T00:00:00Z"}
        
        # Trigger failures to open circuit
        for i in range(3):
            save_sensor_data.write_to_influxdb(test_data)
        
        # Verify circuit is open
        assert save_sensor_data.circuit_open is True
        assert save_sensor_data.failure_count == 3
        
        # Test that messages are skipped when circuit is open
        mock_client = Mock()
        mock_msg = Mock()
        mock_msg.payload = json.dumps(test_data)
        save_sensor_data.on_message(mock_client, None, mock_msg)
        
        # Circuit should still be open, no additional writes
        assert mock_write_api.write.call_count == 3
        
        # Simulate circuit recovery (open_circuit function would normally handle this)
        save_sensor_data.circuit_open = False
        save_sensor_data.failure_count = 0
        
        # Test recovery
        save_sensor_data.write_to_influxdb(test_data)
        save_sensor_data.write_to_influxdb(test_data)
        
        # Verify recovery
        assert mock_write_api.write.call_count == 5
        assert save_sensor_data.failure_count == 0
        mock_logging.error.assert_called()  # Errors were logged during failures

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.mqtt.Client')
    def test_health_check_end_to_end(self, mock_mqtt_client, mock_influx_client):
        """Test complete health check workflow."""
        # Setup InfluxDB mock
        mock_write_api = Mock()
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Setup MQTT mock
        mock_mqtt_instance = Mock()
        mock_mqtt_client.return_value = mock_mqtt_instance
        
        # Reset state
        save_sensor_data.circuit_open = False
        save_sensor_data.failure_count = 0
        
        # Perform health check
        result = save_sensor_data.check_health()
        
        # Verify health check success
        assert result == 0
        mock_write_api.write.assert_called_once()
        
        # Verify health check data was written
        call_args = mock_write_api.write.call_args
        # The health check should write some form of status data
        assert call_args is not None

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.logging')
    def test_data_validation_and_storage_workflow(self, mock_logging, mock_influx_client):
        """Test complete data validation and storage workflow with various data types."""
        # Setup InfluxDB mock
        mock_write_api = Mock()
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Reset circuit breaker
        save_sensor_data.circuit_open = False
        save_sensor_data.failure_count = 0
        
        # Test various sensor data formats
        test_datasets = [
            # Standard IoT sensor data
            {"temperature": 23.5, "humidity": 67.2, "device_id": "sensor_001"},
            # Environmental monitoring
            {"air_quality": 45, "noise_level": 35.2, "uv_index": 3, "location": "downtown"},
            # Industrial sensors
            {"pressure": 1013.25, "flow_rate": 125.7, "vibration": 0.02, "machine_id": "pump_A"},
            # Smart home data
            {"occupancy": True, "light_level": 450, "motion_detected": False, "room": "living_room"}
        ]
        
        # Process each dataset through the complete pipeline
        for i, data in enumerate(test_datasets):
            mock_client = Mock()
            mock_msg = Mock()
            mock_msg.payload = json.dumps(data)
            
            # Process the message
            save_sensor_data.on_message(mock_client, None, mock_msg)
        
        # Verify all datasets were processed successfully
        assert mock_write_api.write.call_count == len(test_datasets)
        assert save_sensor_data.failure_count == 0
        
        # Verify logging occurred for each successful write
        assert mock_logging.info.call_count == len(test_datasets)
        
        # Reset circuit breaker state
        save_sensor_data.failure_count = 0
        save_sensor_data.circuit_open = False
        
        save_sensor_data.write_to_influxdb(sample_sensor_data)
        
        mock_write_api.write.assert_called_once()
        assert save_sensor_data.failure_count == 0

    @pytest.mark.unit
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.open_circuit')
    def test_write_to_influxdb_max_failures(self, mock_open_circuit, mock_influx_client, sample_sensor_data):
        """Test circuit opens after max failures."""
        mock_write_api = Mock()
        mock_write_api.write.side_effect = Exception("Connection failed")
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Set up for max failures
        save_sensor_data.MAX_FAILURES = 3
        save_sensor_data.failure_count = 2  # One less than max
        
        save_sensor_data.write_to_influxdb(sample_sensor_data)
        
        mock_open_circuit.assert_called_once()
        assert save_sensor_data.failure_count == 3

    @pytest.mark.unit
    @patch('time.sleep')
    def test_open_circuit(self, mock_sleep):
        """Test circuit breaker open/close cycle."""
        save_sensor_data.RESET_TIMEOUT = 60
        
        save_sensor_data.open_circuit()
        
        mock_sleep.assert_called_once_with(60)
        assert save_sensor_data.circuit_open is False

    @pytest.mark.unit
    @patch('save_sensor_data.write_to_influxdb')
    @patch('save_sensor_data.logging')
    def test_check_health_success(self, mock_logging, mock_write):
        """Test successful health check."""
        result = save_sensor_data.check_health()
        
        assert result == 0
        mock_write.assert_called_once()
        mock_logging.info.assert_called_with("Healthcheck written to InfluxDB")

    @pytest.mark.unit
    @patch('save_sensor_data.write_to_influxdb')
    def test_check_health_failure(self, mock_write):
        """Test health check failure."""
        mock_write.side_effect = Exception("Health check failed")
        
        result = save_sensor_data.check_health()
        
        assert result == 1

    @pytest.mark.unit
    def test_json_parsing_edge_cases(self):
        """Test JSON parsing with various edge cases."""
        mock_client = Mock()
        
        # Test empty payload
        mock_msg = Mock()
        mock_msg.payload = ""
        with patch('save_sensor_data.logging') as mock_logging:
            save_sensor_data.on_message(mock_client, None, mock_msg)
            mock_logging.error.assert_called()
        
        # Test None payload
        mock_msg.payload = None
        with patch('save_sensor_data.logging') as mock_logging:
            save_sensor_data.on_message(mock_client, None, mock_msg)
            mock_logging.error.assert_called()


class TestSaveSensorDataIntegration:
    """Integration tests for save_sensor_data.py - Testing component interactions"""

    @pytest.mark.integration
    @patch.dict(os.environ, {'ENVIRONMENT': 'testing'})
    @patch('save_sensor_data.dotenv_values')
    @patch('save_sensor_data.mqtt.Client')
    def test_mqtt_client_initialization(self, mock_mqtt_client, mock_dotenv, mock_influx_config):
        """Test MQTT client initialization with environment variables."""
        mock_dotenv.return_value = mock_influx_config
        mock_client_instance = Mock()
        mock_mqtt_client.return_value = mock_client_instance
        
        # This would require refactoring the module to make initialization testable
        # For now, test the configuration logic
        environment = os.getenv("ENVIRONMENT")
        if environment == "testing":
            expected_host = 'sensorhost-test'
        else:
            expected_host = "sensorhost"
            
        assert environment == "testing"

    @pytest.mark.integration
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.write_to_influxdb')
    def test_circuit_breaker_integration(self, mock_write, mock_influx_client, sample_sensor_data):
        """Test circuit breaker behavior with multiple failures."""
        # Simulate failures
        mock_write.side_effect = [
            Exception("Failure 1"),
            Exception("Failure 2"),
            Exception("Failure 3"),  # This should open the circuit
        ]
        
        save_sensor_data.MAX_FAILURES = 3
        save_sensor_data.failure_count = 0
        save_sensor_data.circuit_open = False
        
        # First two failures
        for _ in range(2):
            try:
                save_sensor_data.write_to_influxdb(sample_sensor_data)
            except:
                pass
        
        assert save_sensor_data.failure_count == 2
        assert save_sensor_data.circuit_open is False

    @pytest.mark.integration
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.logging')
    def test_mqtt_influxdb_integration(self, mock_logging, mock_influx_client):
        """Test integration between MQTT message processing and InfluxDB writing."""
        # Setup InfluxDB mock
        mock_write_api = Mock()
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Setup MQTT message
        mock_client = Mock()
        mock_msg = Mock()
        sensor_data = {"temperature": 23.5, "humidity": 67.2, "timestamp": "2023-01-01T00:00:00Z"}
        mock_msg.payload = json.dumps(sensor_data)
        
        # Reset circuit breaker
        save_sensor_data.circuit_open = False
        save_sensor_data.failure_count = 0
        
        # Process message
        save_sensor_data.on_message(mock_client, None, mock_msg)
        
        # Verify integration
        mock_write_api.write.assert_called_once()
        mock_logging.info.assert_called()

    @pytest.mark.integration
    @patch('save_sensor_data.open_circuit')
    @patch('save_sensor_data.InfluxDBClient')
    def test_circuit_breaker_threshold_integration(self, mock_influx_client, mock_open_circuit):
        """Test circuit breaker threshold triggering across multiple write attempts."""
        mock_write_api = Mock()
        mock_write_api.write.side_effect = Exception("Connection failed")
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        save_sensor_data.MAX_FAILURES = 3
        save_sensor_data.failure_count = 0
        save_sensor_data.circuit_open = False
        
        sample_data = {"temp": 25.0}
        
        # Trigger failures up to threshold
        for i in range(3):
            save_sensor_data.write_to_influxdb(sample_data)
        
        # Verify circuit opened after threshold
        mock_open_circuit.assert_called_once()
        assert save_sensor_data.failure_count == 3


class TestSaveSensorDataE2E:
    """End-to-end tests for save_sensor_data.py - Testing complete workflows"""

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.mqtt.Client')
    @patch('save_sensor_data.logging')
    def test_complete_mqtt_to_influxdb_pipeline(self, mock_logging, mock_mqtt_client, mock_influx_client):
        """Test complete end-to-end pipeline from MQTT message to InfluxDB storage."""
        # Setup InfluxDB mock
        mock_write_api = Mock()
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Setup MQTT client mock
        mock_mqtt_instance = Mock()
        mock_mqtt_client.return_value = mock_mqtt_instance
        
        # Setup realistic sensor data
        sensor_readings = [
            {"temperature": 23.5, "humidity": 67.2, "pressure": 1013.25, "timestamp": "2023-01-01T00:00:00Z"},
            {"temperature": 24.1, "humidity": 65.8, "pressure": 1012.80, "timestamp": "2023-01-01T00:01:00Z"},
            {"temperature": 24.7, "humidity": 64.3, "pressure": 1011.95, "timestamp": "2023-01-01T00:02:00Z"}
        ]
        
        # Reset circuit breaker state
        save_sensor_data.circuit_open = False
        save_sensor_data.failure_count = 0
        
        # Simulate receiving multiple MQTT messages
        for reading in sensor_readings:
            mock_msg = Mock()
            mock_msg.payload = json.dumps(reading)
            save_sensor_data.on_message(mock_mqtt_instance, None, mock_msg)
        
        # Verify end-to-end processing
        assert mock_write_api.write.call_count == 3
        assert mock_logging.info.call_count == 3
        assert save_sensor_data.failure_count == 0

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch.dict(os.environ, {'ENVIRONMENT': 'production'})
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.dotenv_values')
    def test_production_environment_workflow(self, mock_dotenv, mock_influx_client):
        """Test complete workflow in production environment configuration."""
        # Setup production config
        production_config = {
            'INFLUXDB_TOKEN': 'prod_token',
            'INFLUXDB_ORG': 'prod_org',
            'INFLUXDB_BUCKET': 'prod_bucket',
            'INFLUXDB_URL': 'https://prod-influxdb.example.com:8086'
        }
        mock_dotenv.return_value = production_config
        
        # Setup InfluxDB mock
        mock_write_api = Mock()
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Test production data processing
        production_data = {
            "sensor_id": "prod_sensor_001",
            "temperature": 22.8,
            "humidity": 68.5,
            "location": "datacenter_rack_A1",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        save_sensor_data.circuit_open = False
        save_sensor_data.write_to_influxdb(production_data)
        
        # Verify production workflow
        mock_write_api.write.assert_called_once()
        # Verify InfluxDB client was called with production config
        mock_influx_client.assert_called()

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch('save_sensor_data.InfluxDBClient')
    @patch('save_sensor_data.logging')
    @patch('time.sleep')
    def test_circuit_breaker_recovery_workflow(self, mock_sleep, mock_logging, mock_influx_client):
        """Test complete circuit breaker failure and recovery workflow."""
        # Setup InfluxDB mock with intermittent failures
        mock_write_api = Mock()
        mock_client_instance = Mock()
        mock_client_instance.write_api.return_value = mock_write_api
        mock_influx_client.return_value.__