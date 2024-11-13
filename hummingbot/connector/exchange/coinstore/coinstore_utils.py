from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

# Centralized exchange flag
CENTRALIZED = True
EXAMPLE_PAIR = "BTCUSDT"  # Example trading pair, ensure it matches Coinstore's API format

# Default trading fees for Coinstore
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0002"),  # Coinstore's actual maker fee (0.2%)
    taker_percent_fee_decimal=Decimal("0.00025"),  # Coinstore's actual taker fee (0.25%)
    buy_percent_fee_deducted_from_returns=True
)

def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled based on its exchange information
    :param exchange_info: the exchange information for a trading pair
    :return: True if the trading pair is enabled, False otherwise
    """
    is_spot = False
    is_trading = False

    if exchange_info.get("status", None) == "TRADING":
        is_trading = True

    # Permissions, typically in 'permissionSets', may vary; adjust based on Coinstore API specifics
    permissions_sets = exchange_info.get("permissionSets", list())
    for permission_set in permissions_sets:
        # PermissionSet is a list, check if it contains "SPOT" or similar for Coinstore
        if "SPOT" in permission_set:
            is_spot = True
            break

    return is_trading and is_spot


class CoinstoreConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="coinstore", const=True, client_data=None)
    coinstore_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Coinstore API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    coinstore_api_secret: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Coinstore API secret",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    class Config:
        title = "coinstore"


KEYS = CoinstoreConfigMap.construct()

# Define other domains if Coinstore has them; otherwise, keep these as empty
OTHER_DOMAINS = []
OTHER_DOMAINS_PARAMETER = {}
OTHER_DOMAINS_EXAMPLE_PAIR = {}
OTHER_DOMAINS_DEFAULT_FEES = {}

# Remove or define additional config maps for other domains if Coinstore has them
OTHER_DOMAINS_KEYS = {}
