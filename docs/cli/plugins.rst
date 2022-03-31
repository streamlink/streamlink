Plugin specific usage
=====================

Authenticating with Crunchyroll
-------------------------------

Crunchyroll requires authenticating with a premium account to access some of
their content. To do so, the plugin provides a couple of options to input your
information, :option:`--crunchyroll-username` and :option:`--crunchyroll-password`.

You can login like this:

.. sourcecode:: console

    $ streamlink --crunchyroll-username=xxxx --crunchyroll-password=xxx https://crunchyroll.com/a-crunchyroll-episode-link

.. note::

    If you omit the password, streamlink will ask for it.

Once logged in, the plugin makes sure to save the session credentials to avoid
asking your username and password again.

Nevertheless, these credentials are valid for a limited amount of time, so it
might be a good idea to save your username and password in your
:ref:`configuration file <cli/config:Configuration file>` anyway.

.. warning::

    The API this plugin uses isn't supposed to be available on desktop
    computers. The plugin tries to blend in as a valid device using custom
    headers and following the API's usual flow (e.g. reusing credentials), but
    this does not assure that your account will be safe from being spotted for
    unusual behavior.

HTTP proxy with Crunchyroll
^^^^^^^^^^^^^^^^^^^^^^^^^^^
To be able to stream region locked content, you can use Streamlink's proxy
options, which are described in the :ref:`Proxy Support <cli/proxy:Proxy Support>` section.

When doing this, it's possible that access to the stream will still be denied;
this can happen because the session and credentials used by the plugin
were obtained while being logged from your own region, and the server still assumes
you're in that region.

For cases like this, the plugin provides the :option:`--crunchyroll-purge-credentials`
option, which removes your saved session and credentials and tries to log
in again using your username and password.

Authenticating with FunimationNow
---------------------------------
Like Crunchyroll, the FunimationNow plugin requires authenticating with a premium account to access some
content: :option:`--funimation-email`, :option:`--funimation-password`. In addition, this plugin requires
the ``incap_ses`` cookie to be sent with each HTTP request (see issue #2088). This unique session cookie
can be found in your browser and sent via the :option:`--http-cookie` option.

.. sourcecode:: console

    $ streamlink --funimation-email='xxx' --funimation-password='xxx' --http-cookie 'incap_ses_xxx=xxxx=' https://funimation.com/shows/show/an-episode-link

.. note::

    There are multiple ways to retrieve the required cookie. For more
    information on browser cookies, please consult the following:

    - `What are cookies? <https://en.wikipedia.org/wiki/HTTP_cookie>`_
