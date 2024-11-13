from typing import Callable, Optional

from hummingbot.connector.exchange.coinstore import coinstore_constants as CONSTANTS
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, RESTMethod
from hummingbot.core.web_assistant.rest_pre_processors import RESTPreProcessorBase
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.connector.utils import TimeSynchronizerRESTPreProcessor

class CoinstoreRESTPreProcessor(RESTPreProcessorBase):
    async def pre_process(self, request: RESTRequest) -> RESTRequest:
        if request.headers is None:
            request.headers = {}
        # Generates generic headers required
        headers_generic = {}
        headers_generic["Accept"] = "application/json"
        headers_generic["Content-Type"] = "application/json"
        # Headers signature to identify user as an HB liquidity provider.
        request.headers = dict(list(request.headers.items()) + list(headers_generic.items()))
        return request


def public_rest_url(path_url: str, domain: Optional[str] = None) -> str:
    """
    Creates a full URL for provided private REST endpoint
    :param path_url: a private REST endpoint
    :param domain: domain to connect to
    :return: the full URL to the endpoint
    """
    return CONSTANTS.REST_URL + path_url


def private_rest_url(path_url: str, domain: Optional[str] = None) -> str:
    return public_rest_url(path_url=path_url)


# Private URL Constructor
def private_rest_url(path_url: str, domain: Optional[str] = None) -> str:
    """
    Constructs a URL for a private Coinstore API endpoint.
    """
    return public_rest_url(path_url=path_url)  # Coinstore does not differentiate public/private base URLs

# Server Time Fetcher
async def get_current_server_time(throttler: Optional[AsyncThrottler] = None) -> float:
    throttler = throttler or create_throttler()
    api_factory = build_api_factory_without_time_synchronizer_pre_processor(throttler=throttler)
    rest_assistant = await api_factory.get_rest_assistant()
    
    response = await rest_assistant.execute_request(
        url=public_rest_url(path_url=CONSTANTS.SERVER_TIME_PATH_URL),
        method=RESTMethod.GET,
        throttler_limit_id=CONSTANTS.SERVER_TIME_PATH_URL,
    )
    # Adjust to the actual key for server time from the Coinstore API documentation
    server_time = response["time"]  # Replace "time" if Coinstore uses a different key
    return server_time

# API Factory Builder with Time Synchronizer (if time sync is required)
def build_api_factory(
    throttler: Optional[AsyncThrottler] = None,
    time_synchronizer: Optional[TimeSynchronizer] = None,
    auth: Optional[AuthBase] = None,
) -> WebAssistantsFactory:
    throttler = throttler or create_throttler()
    time_synchronizer = time_synchronizer or TimeSynchronizer()
    
    api_factory = WebAssistantsFactory(
        throttler=throttler,
        auth=auth,
        rest_pre_processors=[
            TimeSynchronizerRESTPreProcessor(
                synchronizer=time_synchronizer,
                time_provider=get_current_server_time,
            ),
            CoinstoreRESTPreProcessor(),
        ]
    )
    return api_factory

# API Factory without Time Synchronizer (if time sync is not required)
def build_api_factory_without_time_synchronizer_pre_processor(throttler: AsyncThrottler) -> WebAssistantsFactory:
    return WebAssistantsFactory(throttler=throttler)

# Throttler Creator
def create_throttler() -> AsyncThrottler:
    return AsyncThrottler(CONSTANTS.RATE_LIMITS)