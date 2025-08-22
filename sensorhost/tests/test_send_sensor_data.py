import pytest
import json
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Import the module under test
sys.path.append('sensorhost')
import send_sensor_data


class TestSendSensorDataUnit:
    """Unit tests for send_sensor_data.py - Testing individual functions in isolation"""

    @pytest.mark.unit
    @patch('send_sensor_data.InfluxDBClient')
    def test_query_source_success(self, mock_influx_client, mock_influx_query_result):
        """Test successful InfluxDB query."""
        mock_client_instance = Mock()
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = mock_influx_query_result
        mock_client_instance.query_api.return_value = mock_query_api
        
        result = send_sensor_data.query_source(mock_client_instance)
        
        assert result is not False
        mock_query_api.query_data_frame.assert_called_once()

    @pytest.mark.unit
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.logging')
    def test_query_source_empty_result(self, mock_logging, mock_influx_client):
        """Test query_source with empty result."""
        mock_client_instance = Mock()
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = []  # Empty list
        mock_client_instance.query_api.return_value = mock_query_api
        
        result = send_sensor_data.query_source(mock_client_instance)
        
        assert result is False
        mock_logging.warning.assert_called_with("Query returned an empty list.")

    @pytest.mark.unit
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.logging')
    def test_query_source_exception(self, mock_logging, mock_influx_client):
        """Test query_source exception handling."""
        mock_client_instance = Mock()
        mock_query_api = Mock()
        mock_query_api.query_data_frame.side_effect = Exception("Query failed")
        mock_client_instance.query_api.return_value = mock_query_api
        
        result = send_sensor_data.query_source(mock_client_instance)
        
        assert result is False
        mock_logging.error.assert_called()

    @pytest.mark.unit
    @patch.dict(os.environ, {'ENVIRONMENT': 'production'})
    @patch('send_sensor_data.KafkaProducer')
    def test_connect_kafka_producer_production(self, mock_kafka_producer):
        """Test Kafka producer connection in production environment."""
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        
        producer = send_sensor_data.connect_kafka_producer()
        
        mock_kafka_producer.assert_called_once()
        call_args = mock_kafka_producer.call_args
        assert 'kafka_production:9092' in call_args[1]['bootstrap_servers']

    @pytest.mark.unit
    @patch.dict(os.environ, {'ENVIRONMENT': 'testing'})
    @patch('send_sensor_data.KafkaProducer')
    def test_connect_kafka_producer_testing(self, mock_kafka_producer):
        """Test Kafka producer connection in testing environment."""
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        
        producer = send_sensor_data.connect_kafka_producer()
        
        mock_kafka_producer.assert_called_once()
        call_args = mock_kafka_producer.call_args
        assert 'kafka_testing:9092' in call_args[1]['bootstrap_servers']

    @pytest.mark.unit
    def test_connect_kafka_producer_invalid_environment(self):
        """Test Kafka producer with invalid environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'invalid'}):
            with pytest.raises(ValueError, match="Unknown environment specified"):
                send_sensor_data.connect_kafka_producer()

    @pytest.mark.unit
    @patch('send_sensor_data.logging')
    def test_publish_success(self, mock_logging):
        """Test successful message publishing."""
        mock_producer = Mock()
        send_sensor_data.kafka_producer = mock_producer
        
        test_message = '{"temp": 25.5, "moisture": 65.2}'
        
        send_sensor_data.publish("test_topic", test_message)
        
        mock_producer.send.assert_called()
        mock_logging.info.assert_called()

    @pytest.mark.unit
    @patch('send_sensor_data.logging')
    def test_publish_dict_message(self, mock_logging):
        """Test publishing dictionary message."""
        mock_producer = Mock()
        send_sensor_data.kafka_producer = mock_producer
        
        test_message = {"temp": 25.5, "moisture": 65.2}
        
        send_sensor_data.publish("test_topic", test_message)
        
        mock_producer.send.assert_called()

    @pytest.mark.unit
    @patch('send_sensor_data.logging')
    @patch('time.sleep')
    def test_publish_with_retries(self, mock_sleep, mock_logging):
        """Test publish with retries on failure."""
        mock_producer = Mock()
        mock_producer.send.side_effect = [Exception("Send failed"), None]  # Fail then succeed
        send_sensor_data.kafka_producer = mock_producer
        
        test_message = '{"temp": 25.5}'
        
        with pytest.raises(Exception):
            send_sensor_data.publish("test_topic", test_message, max_retries=2)

    @pytest.mark.unit
    @patch('send_sensor_data.publish')
    @patch('send_sensor_data.logging')
    def test_check_health_success(self, mock_logging, mock_publish):
        """Test successful health check."""
        result = send_sensor_data.check_health()
        
        assert result == 0
        mock_publish.assert_called_once_with("healthcheck", {"status": "ok"})
        mock_logging.info.assert_called_with("Health check successful")

    @pytest.mark.unit
    @patch('send_sensor_data.publish')
    @patch('send_sensor_data.logging')
    def test_check_health_failure(self, mock_logging, mock_publish):
        """Test health check failure."""
        mock_publish.side_effect = Exception("Publish failed")
        
        result = send_sensor_data.check_health()
        
        assert result == 1
        mock_logging.error.assert_called()


class TestSendSensorDataIntegration:
    """Integration tests for send_sensor_data.py - Testing component interactions"""

    @pytest.mark.integration
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.publish')
    @patch('time.sleep')
    def test_main_loop_single_iteration(self, mock_sleep, mock_publish, mock_influx_client, mock_influx_query_result):
        """Test main loop single iteration with InfluxDB query and Kafka publish integration."""
        # Mock InfluxDB client and query
        mock_client_instance = Mock()
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = mock_influx_query_result
        mock_client_instance.query_api.return_value = mock_query_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Mock sleep to break the infinite loop
        mock_sleep.side_effect = [KeyboardInterrupt()]
        
        with pytest.raises(KeyboardInterrupt):
            send_sensor_data.main()
        
        mock_publish.assert_called()
        mock_sleep.assert_called_with(300)  # 5-minute sleep

    @pytest.mark.integration
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.logging')
    @patch('time.sleep')
    def test_main_loop_exception_handling(self, mock_sleep, mock_logging, mock_influx_client):
        """Test main loop exception handling across components."""
        mock_influx_client.side_effect = Exception("Connection failed")
        
        result = send_sensor_data.main()
        
        assert result is False
        mock_logging.error.assert_called()

    @pytest.mark.integration
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.KafkaProducer')
    @patch('send_sensor_data.logging')
    def test_influxdb_kafka_integration(self, mock_logging, mock_kafka_producer, mock_influx_client):
        """Test integration between InfluxDB query and Kafka publishing."""
        # Setup InfluxDB mock
        mock_client_instance = Mock()
        mock_query_api = Mock()
        mock_query_result = pd.DataFrame({'temp': [25.5], 'moisture': [65.2]})
        mock_query_api.query_data_frame.return_value = mock_query_result
        mock_client_instance.query_api.return_value = mock_query_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Setup Kafka mock
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        send_sensor_data.kafka_producer = mock_producer_instance
        
        # Execute the integration
        data = send_sensor_data.query_source(mock_client_instance)
        if data is not False:
            send_sensor_data.publish("sensor_data", data.to_json())
        
        # Verify integration
        mock_query_api.query_data_frame.assert_called_once()
        mock_producer_instance.send.assert_called_once()


class TestSendSensorDataE2E:
    """End-to-end tests for send_sensor_data.py - Testing complete workflows"""

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch.dict(os.environ, {'ENVIRONMENT': 'testing'})
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.KafkaProducer')
    @patch('time.sleep')
    def test_complete_sensor_data_pipeline(self, mock_sleep, mock_kafka_producer, mock_influx_client):
        """Test complete end-to-end sensor data pipeline from query to publish."""
        # Setup realistic data
        sensor_data = pd.DataFrame({
            'timestamp': ['2023-01-01T00:00:00Z'],
            'temperature': [23.5],
            'humidity': [67.2],
            'pressure': [1013.25]
        })
        
        # Setup InfluxDB mock
        mock_client_instance = Mock()
        mock_query_api = Mock()
        mock_query_api.query_data_frame.return_value = sensor_data
        mock_client_instance.query_api.return_value = mock_query_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        # Setup Kafka mock
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        
        # Mock sleep to exit after one iteration
        mock_sleep.side_effect = [KeyboardInterrupt()]
        
        # Run the complete pipeline
        with pytest.raises(KeyboardInterrupt):
            send_sensor_data.main()
        
        # Verify end-to-end flow
        mock_influx_client.assert_called()
        mock_kafka_producer.assert_called()
        mock_query_api.query_data_frame.assert_called()
        mock_producer_instance.send.assert_called()

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch.dict(os.environ, {'ENVIRONMENT': 'production'})
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.KafkaProducer')
    def test_production_environment_configuration(self, mock_kafka_producer, mock_influx_client):
        """Test end-to-end configuration in production environment."""
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        
        # Test Kafka producer configuration
        producer = send_sensor_data.connect_kafka_producer()
        
        # Verify production configuration
        call_args = mock_kafka_producer.call_args
        assert 'kafka_production:9092' in call_args[1]['bootstrap_servers']
        
        # Test health check in production context
        send_sensor_data.kafka_producer = mock_producer_instance
        result = send_sensor_data.check_health()
        
        assert result == 0
        mock_producer_instance.send.assert_called()

    @pytest.mark.e2e
    @pytest.mark.slow
    @patch('send_sensor_data.InfluxDBClient')
    @patch('send_sensor_data.KafkaProducer')
    @patch('send_sensor_data.logging')
    def test_error_recovery_workflow(self, mock_logging, mock_kafka_producer, mock_influx_client):
        """Test end-to-end error recovery and resilience."""
        # Setup intermittent failures
        mock_client_instance = Mock()
        mock_query_api = Mock()
        mock_query_api.query_data_frame.side_effect = [
            Exception("Network timeout"),
            pd.DataFrame({'temp': [25.0]})  # Recovery
        ]
        mock_client_instance.query_api.return_value = mock_query_api
        mock_influx_client.return_value.__enter__.return_value = mock_client_instance
        
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        send_sensor_data.kafka_producer = mock_producer_instance
        
        # Test first failure
        result1 = send_sensor_data.query_source(mock_client_instance)
        assert result1 is False
        
        # Test recovery
        result2 = send_sensor_data.query_source(mock_client_instance)
        assert result2 is not False
        
        # Verify error logging and recovery
        mock_logging.error.assert_called()
        assert mock_query_api.query_data_frame.call_count == 2