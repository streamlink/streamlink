Proxy Support
-------------

You can use the :option:`--http-proxy` option to change the proxy server
that Streamlink will use for HTTP and HTTPS requests. :option:`--http-proxy` sets
the proxy for all HTTP and HTTPS requests, including WebSocket connections.

If separate proxies for each protocol are required, they can be set using
environment variables - see the `Requests Proxies Documentation`_.

Both HTTP and SOCKS proxies are supported, as well as authentication in each of them.

.. note::
    When using a SOCKS proxy, the ``socks4`` and ``socks5`` schemes mean that DNS lookups are done
    locally, rather than on the proxy server. To have the proxy server perform the DNS lookups, the
    ``socks4a`` and ``socks5h`` schemes should be used instead.

.. code-block:: console

    $ streamlink --http-proxy "http://address:port"
    $ streamlink --http-proxy "https://address:port"
    $ streamlink --http-proxy "socks4a://address:port"
    $ streamlink --http-proxy "socks5h://address:port"

.. _Requests Proxies Documentation: https://requests.readthedocs.io/en/latest/user/advanced/#proxies
