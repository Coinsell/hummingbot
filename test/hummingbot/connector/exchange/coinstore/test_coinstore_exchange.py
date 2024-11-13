import unittest
from unittest.mock import patch, MagicMock
from coinstore_exchange import CoinstoreExchange
from hummingbot.core.api_error import APIError
from hummingbot.core.data_type.order import Order
from hummingbot.core.data_type.in_flight_order import InFlightOrder
from decimal import Decimal
from hummingbot.core.api_throttler import AsyncThrottler


class TestCoinstoreExchange(unittest.TestCase):

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_create_order_successful(self, mock_send_rest_request):
        # Setup mock response for create order
        mock_send_rest_request.return_value = {
            "symbol": "BTC-USDT",
            "orderId": 123456,
            "clientOrderId": "testClientOrderId",
            "price": "50000",
            "origQty": "1",
            "status": "NEW"
        }

        exchange = CoinstoreExchange()
        order = Order(
            symbol="BTC-USDT",
            price=Decimal("50000"),
            amount=Decimal("1"),
            order_type="LIMIT",
            trade_type="BUY"
        )

        result = exchange.create_order(order)

        self.assertEqual(result["symbol"], "BTC-USDT")
        self.assertEqual(result["orderId"], 123456)
        self.assertEqual(result["status"], "NEW")

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_cancel_order_successful(self, mock_send_rest_request):
        # Setup mock response for cancel order
        mock_send_rest_request.return_value = {
            "symbol": "BTC-USDT",
            "orderId": 123456,
            "origClientOrderId": "testClientOrderId",
            "status": "CANCELED"
        }

        exchange = CoinstoreExchange()
        in_flight_order = InFlightOrder(
            client_order_id="testClientOrderId",
            exchange_order_id="123456",
            price=Decimal("50000"),
            amount=Decimal("1"),
            status="NEW"
        )

        result = exchange.cancel_order(in_flight_order)

        self.assertEqual(result["status"], "CANCELED")
        self.assertEqual(result["orderId"], 123456)

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_order_status_successful(self, mock_send_rest_request):
        # Setup mock response for order status check
        mock_send_rest_request.return_value = {
            "symbol": "BTC-USDT",
            "orderId": 123456,
            "status": "FILLED",
            "executedQty": "1",
            "origQty": "1",
            "price": "50000"
        }

        exchange = CoinstoreExchange()
        in_flight_order = InFlightOrder(
            client_order_id="testClientOrderId",
            exchange_order_id="123456",
            price=Decimal("50000"),
            amount=Decimal("1"),
            status="NEW"
        )

        result = exchange.get_order_status(in_flight_order)

        self.assertEqual(result["status"], "FILLED")
        self.assertEqual(result["executedQty"], "1")
        self.assertEqual(result["price"], "50000")

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_get_order_fills_successful(self, mock_send_rest_request):
        # Setup mock response for order fills
        mock_send_rest_request.return_value = [
            {
                "symbol": "BTC-USDT",
                "id": 7890,
                "orderId": 123456,
                "price": "50000",
                "qty": "1",
                "quoteQty": "50000",
                "commission": "0.01",
                "commissionAsset": "USDT",
                "time": 1499865549590,
                "isBuyer": True,
                "isMaker": False,
                "isBestMatch": True
            }
        ]

        exchange = CoinstoreExchange()
        in_flight_order = InFlightOrder(
            client_order_id="testClientOrderId",
            exchange_order_id="123456",
            price=Decimal("50000"),
            amount=Decimal("1"),
            status="FILLED"
        )

        result = exchange.get_order_fills(in_flight_order)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price"], "50000")
        self.assertEqual(result[0]["qty"], "1")
        self.assertEqual(result[0]["commissionAsset"], "USDT")

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_fetch_order_book_successful(self, mock_send_rest_request):
        # Setup mock response for order book
        mock_send_rest_request.return_value = {
            "symbol": "BTC-USDT",
            "bids": [
                ["50000", "1"],
                ["49900", "2"]
            ],
            "asks": [
                ["51000", "1"],
                ["52000", "1"]
            ]
        }

        exchange = CoinstoreExchange()
        order_book = exchange.get_order_book("BTC-USDT")

        self.assertIn("bids", order_book)
        self.assertIn("asks", order_book)
        self.assertEqual(order_book["symbol"], "BTC-USDT")
        self.assertEqual(order_book["bids"][0][0], "50000")
        self.assertEqual(order_book["asks"][1][0], "52000")

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_get_markets_data_successful(self, mock_send_rest_request):
        # Setup mock response for markets data
        mock_send_rest_request.return_value = [
            {
                "symbol": "BTC-USDT",
                "status": "TRADING",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "pricePrecision": 2,
                "quantityPrecision": 2
            }
        ]

        exchange = CoinstoreExchange()
        markets_data = exchange.get_markets_data()

        self.assertGreater(len(markets_data), 0)
        self.assertEqual(markets_data[0]["symbol"], "BTC-USDT")
        self.assertEqual(markets_data[0]["baseAsset"], "BTC")
        self.assertEqual(markets_data[0]["quoteAsset"], "USDT")

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_get_account_balance_successful(self, mock_send_rest_request):
        # Setup mock response for account balance
        mock_send_rest_request.return_value = [
            {
                "asset": "USDT",
                "free": "1000",
                "locked": "0"
            }
        ]

        exchange = CoinstoreExchange()
        balances = exchange.get_account_balance()

        self.assertGreater(len(balances), 0)
        self.assertEqual(balances[0]["asset"], "USDT")
        self.assertEqual(balances[0]["free"], "1000")

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_order_status_with_error(self, mock_send_rest_request):
        # Setup mock error response
        mock_send_rest_request.side_effect = APIError("Order not found", 404)

        exchange = CoinstoreExchange()
        in_flight_order = InFlightOrder(
            client_order_id="nonexistentOrder",
            exchange_order_id="nonexistentId",
            price=Decimal("50000"),
            amount=Decimal("1"),
            status="NEW"
        )

        with self.assertRaises(APIError):
            exchange.get_order_status(in_flight_order)

    @patch("hummingbot.core.api_throttler.AsyncThrottler._throttle")
    def test_throttling_behavior(self, mock_throttle):
        # This test checks if throttling behavior is working correctly
        mock_throttle.return_value = None
        exchange = CoinstoreExchange()
        exchange.throttler = AsyncThrottler()

        # Simulate a request
        exchange._send_rest_request("GET", "/some_endpoint", {})

        # Check that throttle was called
        mock_throttle.assert_called()

    @patch("coinstore_exchange.CoinstoreExchange._send_rest_request")
    def test_get_symbol_info(self, mock_send_rest_request):
        # Setup mock response for symbol info
        mock_send_rest_request.return_value = {
            "symbol": "BTC-USDT",
            "status": "TRADING",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "pricePrecision": 2,
            "quantityPrecision": 2
        }

        exchange = CoinstoreExchange()
        symbol_info = exchange.get_symbol_info("BTC-USDT")

        self.assertEqual(symbol_info["symbol"], "BTC-USDT")
        self.assertEqual(symbol_info["baseAsset"], "BTC")
        self.assertEqual(symbol_info["quoteAsset"], "USDT")


if __name__ == '__main__':
    unittest.main()