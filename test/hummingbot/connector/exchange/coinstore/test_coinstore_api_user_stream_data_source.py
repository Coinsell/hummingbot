import asyncio
import time
import hmac
import hashlib
from unittest import TestCase
from unittest.mock import MagicMock
from copy import copy
from hummingbot.connector.exchange.coinstore.coinstore_api_user_stream_data_source import CoinstoreAPIUserStreamDataSource
from hummingbot.connector.exchange.coinstore.coinstore_auth import CoinstoreAuth
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest


class CoinstoreAPIUserStreamDataSourceTests(TestCase):

    def setUp(self) -> None:
        """Set up necessary mock objects and test environment."""
        self._api_key = "testApiKey"
        self._secret = "testSecret"

    def async_run_with_timeout(self, coroutine: asyncio.Future, timeout: float = 1):
        """Helper method to run an asynchronous coroutine with a timeout."""
        ret = asyncio.get_event_loop().run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    def test_rest_authenticate(self):
        """Test the authentication logic for REST requests."""
        now = 1234567890.000  # Mocked current time
        mock_time_provider = MagicMock()
        mock_time_provider.time.return_value = now

        # Params for testing authentication
        params = {
            "symbol": "LTCBTC",
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": 1,
            "price": "0.1",
        }
        full_params = copy(params)

        # Create authentication object
        auth = CoinstoreAuth(api_key=self._api_key, secret_key=self._secret, time_provider=mock_time_provider)
        request = RESTRequest(method=RESTMethod.GET, params=params, is_auth_required=True)
        
        # Perform the authentication
        configured_request = self.async_run_with_timeout(auth.rest_authenticate(request))

        # Prepare expected signature
        full_params.update({"timestamp": 1234567890000})
        encoded_params = "&".join([f"{key}={value}" for key, value in full_params.items()])
        expected_signature = hmac.new(
            self._secret.encode("utf-8"),
            encoded_params.encode("utf-8"),
            hashlib.sha256).hexdigest()

        # Validate timestamp and signature in the request
        self.assertEqual(now * 1e3, configured_request.params["timestamp"])
        self.assertEqual(configured_request.params["signature"], expected_signature)

    def test_get_listen_key_successful(self):
        """Test for getting the listen key successfully."""
        mock_response = {"listenKey": "testListenKey"}
        mock_rest_client = MagicMock()
        mock_rest_client.get.return_value = mock_response

        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, rest_client=mock_rest_client)
        listen_key = self.async_run_with_timeout(data_source.get_listen_key())

        # Check if listen key is returned and correct
        self.assertEqual(listen_key, "testListenKey")
        mock_rest_client.get.assert_called_once_with("/api/v1/user/stream", params={"apiKey": self._api_key})

    def test_get_listen_key_log_exception(self):
        """Test for logging exception if getting the listen key fails."""
        mock_rest_client = MagicMock()
        mock_rest_client.get.side_effect = Exception("API Error")

        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, rest_client=mock_rest_client)
        
        with self.assertRaises(Exception):
            self.async_run_with_timeout(data_source.get_listen_key())
        mock_rest_client.get.assert_called_once_with("/api/v1/user/stream", params={"apiKey": self._api_key})

    def test_ping_listen_key_successful(self):
        """Test the ping functionality for keeping the listen key alive."""
        mock_response = {"status": "OK"}
        mock_rest_client = MagicMock()
        mock_rest_client.post.return_value = mock_response

        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, rest_client=mock_rest_client)
        result = self.async_run_with_timeout(data_source.ping_listen_key("testListenKey"))

        # Check if the result is successful
        self.assertTrue(result)
        mock_rest_client.post.assert_called_once_with("/api/v1/user/stream/ping", params={"apiKey": self._api_key, "listenKey": "testListenKey"})

    def test_ping_listen_key_log_exception(self):
        """Test for logging exception if pinging the listen key fails."""
        mock_rest_client = MagicMock()
        mock_rest_client.post.side_effect = Exception("API Error")

        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, rest_client=mock_rest_client)
        
        with self.assertRaises(Exception):
            self.async_run_with_timeout(data_source.ping_listen_key("testListenKey"))
        mock_rest_client.post.assert_called_once_with("/api/v1/user/stream/ping", params={"apiKey": self._api_key, "listenKey": "testListenKey"})

    def test_manage_listen_key_task_loop_keep_alive_successful(self):
        """Test for managing the listen key task loop and keeping alive successfully."""
        mock_response = {"status": "OK"}
        mock_rest_client = MagicMock()
        mock_rest_client.post.return_value = mock_response

        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, rest_client=mock_rest_client)
        
        self.async_run_with_timeout(data_source._manage_listen_key_task_loop("testListenKey"))
        mock_rest_client.post.assert_called_with("/api/v1/user/stream/ping", params={"apiKey": self._api_key, "listenKey": "testListenKey"})

    def test_manage_listen_key_task_loop_keep_alive_failed(self):
        """Test for failure while managing the listen key task loop."""
        mock_rest_client = MagicMock()
        mock_rest_client.post.side_effect = Exception("API Error")

        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, rest_client=mock_rest_client)
        
        with self.assertRaises(Exception):
            self.async_run_with_timeout(data_source._manage_listen_key_task_loop("testListenKey"))
        mock_rest_client.post.assert_called_with("/api/v1/user/stream/ping", params={"apiKey": self._api_key, "listenKey": "testListenKey"})

    def test_listen_for_user_stream_get_listen_key_successful_with_user_update_event(self):
        """Test for successful user stream listening with a user update event."""
        mock_listen_key = "testListenKey"
        mock_ws_client = MagicMock()
        mock_ws_client.connect.return_value = None
        
        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, ws_client=mock_ws_client)
        user_stream = self.async_run_with_timeout(data_source.listen_for_user_stream(mock_listen_key))

        # Check if user stream connection is established
        self.assertTrue(user_stream)
        mock_ws_client.connect.assert_called_once_with(f"wss://api.coinstore.com/user/{mock_listen_key}")

    def test_listen_for_user_stream_connection_failed(self):
        """Test for handling connection failure during user stream listening."""
        mock_listen_key = "testListenKey"
        mock_ws_client = MagicMock()
        mock_ws_client.connect.side_effect = Exception("Connection Error")
        
        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, ws_client=mock_ws_client)
        
        with self.assertRaises(Exception):
            self.async_run_with_timeout(data_source.listen_for_user_stream(mock_listen_key))

    def test_listen_for_user_stream_iter_message_throws_exception(self):
        """Test if an exception is thrown during message iteration in the user stream."""
        mock_listen_key = "testListenKey"
        mock_ws_client = MagicMock()
        mock_ws_client.connect.return_value = None
        mock_ws_client.recv.side_effect = Exception("Message Iteration Error")
        
        data_source = CoinstoreAPIUserStreamDataSource(api_key=self._api_key, secret_key=self._secret, ws_client=mock_ws_client)
        
        with self.assertRaises(Exception):
            self.async_run_with_timeout(data_source.listen_for_user_stream(mock_listen_key))
