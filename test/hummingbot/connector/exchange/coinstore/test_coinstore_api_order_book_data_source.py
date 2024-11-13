import unittest
from unittest.mock import patch, AsyncMock
from hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source import CoinstoreAPIOrderBookDataSource
from hummingbot.connector.exchange.coinstore.coinstore_exchange import CoinstoreExchange
from hummingbot.core.data_type.order_book_message import OrderBookMessage, OrderBookMessageType
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from decimal import Decimal

class TestCoinstoreAPIOrderBookDataSource(unittest.TestCase):

    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.CoinstoreExchange")
    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.WebAssistantsFactory")
    def setUp(self, MockWebAssistantsFactory, MockCoinstoreExchange):
        # Set up the necessary mock objects and instances
        self.mock_connector = MockCoinstoreExchange
        self.mock_api_factory = MockWebAssistantsFactory
        self.mock_connector.get_last_traded_prices = AsyncMock()
        
        self.order_book_data_source = CoinstoreAPIOrderBookDataSource(
            trading_pairs=["BTC-USDT", "ETH-USDT"],
            connector=self.mock_connector,
            api_factory=self.mock_api_factory
        )

    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.WebAssistantsFactory.get_rest_assistant")
    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.web_utils.public_rest_url")
    async def test_get_new_order_book_successful(self, mock_public_rest_url, mock_get_rest_assistant):
        mock_public_rest_url.return_value = "https://mockurl.com"
        mock_rest_assistant = AsyncMock()
        mock_get_rest_assistant.return_value = mock_rest_assistant
        mock_rest_assistant.execute_request.return_value = {
            "data": {"b": [[100, 0.1]], "a": [[101, 0.1]]}
        }

        snapshot = await self.order_book_data_source._request_order_book_snapshot("BTC-USDT")
        self.assertEqual(snapshot["data"]["b"], [[100, 0.1]])
        self.assertEqual(snapshot["data"]["a"], [[101, 0.1]])

    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.WebAssistantsFactory.get_ws_assistant")
    async def test_listen_for_subscriptions_subscribes_to_trades_and_order_diffs(self, mock_get_ws_assistant):
        mock_ws = AsyncMock(spec=WSAssistant)
        mock_get_ws_assistant.return_value = mock_ws
        await self.order_book_data_source._subscribe_channels(mock_ws)

        # Validate if the correct subscribe payload was sent
        self.assertTrue(mock_ws.send.called)
        payload = mock_ws.send.call_args[0][0].payload
        self.assertIn("op", payload)
        self.assertIn("channel", payload)
        self.assertTrue(payload["channel"])

    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.CoinstoreAPIOrderBookDataSource._parse_trade_message")
    async def test_listen_for_trades_successful(self, mock_parse_trade_message):
        raw_trade_message = {
            "data": [{
                "tradeId": 12345,
                "symbol": "BTC-USDT",
                "takerSide": "BUY",
                "volume": 1.2,
                "price": 45000,
                "time": 1609459200000
            }]
        }
        mock_message_queue = AsyncMock()
        await self.order_book_data_source._parse_trade_message(raw_trade_message, mock_message_queue)

        # Check if trade message was put in the queue
        mock_message_queue.put_nowait.assert_called()

    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.CoinstoreAPIOrderBookDataSource._parse_order_book_diff_message")
    async def test_listen_for_order_book_diffs_successful(self, mock_parse_order_book_diff_message):
        raw_diff_message = {
            "symbol": "BTC-USDT",
            "b": [[45000, 1]],
            "a": [[45500, 1]],
        }
        mock_message_queue = AsyncMock()
        await self.order_book_data_source._parse_order_book_diff_message(raw_diff_message, mock_message_queue)

        # Check if diff message was put in the queue
        mock_message_queue.put_nowait.assert_called()

    @patch("hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source.CoinstoreAPIOrderBookDataSource._parse_order_book_snapshot_message")
    async def test_listen_for_order_book_snapshots_successful(self, mock_parse_order_book_snapshot_message):
        snapshot_message = {
            "symbol": "BTC-USDT",
            "b": [[100, 0.5]],
            "a": [[102, 0.5]],
        }
        mock_message_queue = AsyncMock()
        await self.order_book_data_source._parse_order_book_snapshot_message(snapshot_message, mock_message_queue)

        # Check if snapshot message was put in the queue
        mock_message_queue.put_nowait.assert_called()

if __name__ == "__main__":
    unittest.main()