import hashlib
import hmac
import json
from collections import OrderedDict
from typing import Any, Dict
from urllib.parse import urlencode

from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest, WSRequest

class CoinstoreAuth(AuthBase):
    def __init__(self, api_key: str, secret_key: str, time_provider: TimeSynchronizer):
        self.api_key = api_key
        self.secret_key = secret_key
        self.time_provider = time_provider

    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        """
        Adds the server time and the signature to the request, required for authenticated interactions. It also adds
        the required parameter in the request header.
        :param request: the request to be configured for authenticated interaction
        """
        if request.method == RESTMethod.POST:
            request.data = self.add_auth_to_params(params=json.loads(request.data))
        else:
            request.params = self.add_auth_to_params(params=request.params)

        headers = {}
        if request.headers is not None:
            headers.update(request.headers)
        headers.update(self.header_for_authentication())
        request.headers = headers

        return request

    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        """
        This method is intended to configure a websocket request to be authenticated. Coinstore uses an API key for WebSocket authentication.
        :param request: the request to be configured for authenticated interaction
        """
        # WebSocket authentication is done by including the API key in the request headers
        headers = request.headers or {}
        headers.update(self.header_for_authentication())
        request.headers = headers
        return request

    def add_auth_to_params(self, params: Dict[str, Any]):
        timestamp = int(self.time_provider.time() * 1e3)  # Coinstore API expects timestamp in milliseconds

        request_params = OrderedDict(params or {})
        request_params["timestamp"] = timestamp

        signature = self._generate_signature(params=request_params)
        request_params["signature"] = signature

        return request_params

    def header_for_authentication(self) -> Dict[str, str]:
        # Coinstore uses the API key for authentication in headers as "X-COINSTORE-APIKEY"
        return {"X-COINSTORE-APIKEY": self.api_key}

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate the signature using HMAC-SHA256 algorithm as required by Coinstore API
        :param params: The parameters to be signed
        :return: The generated signature as a hexadecimal string
        """
        encoded_params_str = urlencode(params)
        digest = hmac.new(self.secret_key.encode("utf8"), encoded_params_str.encode("utf8"), hashlib.sha256).hexdigest()
        return digest