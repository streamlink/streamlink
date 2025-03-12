from __future__ import annotations

import logging
import time
from urllib.parse import urlparse

import trio
from requests.cookies import RequestsCookieJar

from streamlink.compat import BaseExceptionGroup
from streamlink.session import Streamlink
from streamlink.webbrowser.cdp import CDPClient, CDPClientSession, devtools


log = logging.getLogger(__name__)


class AWSWAF:
    """
    Solves the AWS Web Application Firewall challenge in a locally spawned web browser.
    Headless mode is detected by AWS.
    """

    HOSTNAME = ".token.awswaf.com"
    TOKEN = "aws-waf-token"
    EXPIRATION = 3600 * 24 * 4

    def __init__(self, session: Streamlink):
        self.session = session

    def acquire(self, url: str) -> bool:
        send: trio.MemorySendChannel[str | None]
        receive: trio.MemoryReceiveChannel[str | None]

        data = None
        send, receive = trio.open_memory_channel(1)
        timeout = self.session.get_option("webbrowser-timeout")

        async def on_request(client_session: CDPClientSession, request: devtools.fetch.RequestPaused):
            cookies = request.request.headers.get("Cookie", "")
            cookie = next((cookie for cookie in cookies.split(";") if cookie.startswith(f"{self.TOKEN}=")), None)

            req_url = request.request.url
            hostname = urlparse(req_url).hostname
            # pass through all requests if the cookie wasn't set yet and the request URL is the initial one or an AWS one
            if cookie is None and (req_url == url or hostname and hostname.endswith(self.HOSTNAME)):
                return await client_session.continue_request(request)

            # return cookie once found
            if cookie is not None:
                await send.send(cookie)

            # block all unneeded requests
            return await client_session.fulfill_request(request, body="")

        async def acquire_token(client: CDPClient):
            client_session: CDPClientSession
            async with client.session(max_buffer_size=100) as client_session:
                client_session.add_request_handler(on_request, on_request=True)
                with trio.move_on_after(timeout):
                    async with client_session.navigate(url) as frame_id:
                        await client_session.loaded(frame_id)
                        return await receive.receive()

        try:
            data = CDPClient.launch(self.session, acquire_token)
        except BaseExceptionGroup:
            log.exception("Failed acquiring AWS WAF token")
        except Exception as err:
            log.error(err)

        if not data:
            log.error("No AWS WAF token has been acquired")
            return False

        domain = urlparse(url).hostname
        cookiejar = RequestsCookieJar()
        cookiejar.set(
            *data.split("=", 1),
            domain="" if not domain else f".{domain}",
            expires=time.time() + self.EXPIRATION,
        )
        self.session.http.cookies.update(cookiejar)

        return True
