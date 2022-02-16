import asyncio
import pytest
import sys
from threading import (
    Thread,
)

import websockets

from tests.utils import (
    wait_for_ws,
)
from web3 import Web3
from web3.exceptions import (
    ValidationError,
)
from web3.providers.websocket import (
    PersistentWebSocket,
    WebsocketProvider,
)

if sys.version_info >= (3, 8):
    from asyncio.exceptions import (
        TimeoutError,
    )
else:
    from concurrent.futures import (
        TimeoutError,
    )


@pytest.fixture
def start_websocket_server(open_port):
    event_loop = asyncio.new_event_loop()

    def run_server():
        async def empty_server(websocket, path):
            data = await websocket.recv()
            await asyncio.sleep(0.02)
            await websocket.send(data)

        asyncio.set_event_loop(event_loop)
        server = websockets.serve(empty_server, "127.0.0.1", open_port)
        event_loop.run_until_complete(server)
        event_loop.run_forever()

    thd = Thread(target=run_server)
    thd.start()
    try:
        yield
    finally:
        event_loop.call_soon_threadsafe(event_loop.stop)


@pytest.fixture
def w3(open_port, start_websocket_server):
    # need new event loop as the one used by server is already running
    event_loop = asyncio.new_event_loop()
    endpoint_uri = "ws://127.0.0.1:{}".format(open_port)
    event_loop.run_until_complete(wait_for_ws(endpoint_uri))
    provider = WebsocketProvider(endpoint_uri, websocket_timeout=0.01)
    return Web3(provider)


def test_websocket_provider_timeout(w3):
    with pytest.raises(TimeoutError):
        w3.eth.accounts


def test_restricted_websocket_kwargs():
    invalid_kwargs = {"uri": "ws://127.0.0.1:8546"}
    re_exc_message = r".*found: {0}*".format(set(invalid_kwargs.keys()))
    with pytest.raises(ValidationError, match=re_exc_message):
        WebsocketProvider(websocket_kwargs=invalid_kwargs)


def test_event_loop_argument_deprecated():
    event_loop = asyncio.new_event_loop()
    endpoint_uri = "ws://127.0.0.1:8546"
    websocket_kwargs = {}
    match = (
        "The loop parameter is deprecated and was removed from websocket "
        "provider as of web3 v5. Consider instantiating this class without "
        "passing this argument instead."
    )
    with pytest.warns(
        expected_warning=DeprecationWarning,
        match=match,
    ):
        WebsocketProvider(endpoint_uri, websocket_timeout=0.01, loop=event_loop)
    with pytest.warns(
        expected_warning=DeprecationWarning,
        match=match,
    ):
        PersistentWebSocket(endpoint_uri, websocket_kwargs, loop=event_loop)
    event_loop.close()
