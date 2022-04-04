FunimationNow
=============

Authentication
--------------

Like Crunchyroll, the FunimationNow plugin requires authenticating with a premium account to access some
content: :option:`--funimation-email`, :option:`--funimation-password`. In addition, this plugin requires
the ``incap_ses`` cookie to be sent with each HTTP request (see issue #2088). This unique session cookie
can be found in your browser and sent via the :option:`--http-cookie` option.

.. code-block:: console

    $ streamlink --funimation-email='xxx' --funimation-password='xxx' --http-cookie 'incap_ses_xxx=xxxx=' https://funimation.com/shows/show/an-episode-link

.. note::

    There are multiple ways to retrieve the required cookie. For more
    information on browser cookies, please consult the following:

    - `What are cookies? <https://en.wikipedia.org/wiki/HTTP_cookie>`_
