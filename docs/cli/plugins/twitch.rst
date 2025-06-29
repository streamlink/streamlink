Twitch
======

Authentication
--------------

**In order to get the personal OAuth token from Twitch's website which identifies your account**, open Twitch.tv in your web
browser and after a successful login, open the developer tools by pressing :kbd:`F12` or :kbd:`CTRL+SHIFT+I`. Then navigate to
the "Console" tab or its equivalent of your web browser and execute the following JavaScript snippet, which reads the value of
the ``auth-token`` cookie, if it exists:

.. code-block:: javascript

    document.cookie.split("; ").find(item=>item.startsWith("auth-token="))?.split("=")[1]

Copy the resulting string consisting of 30 alphanumerical characters without any quotations.

The final ``Authorization`` header which will identify your account while requesting a streaming access token can then be set
via Streamlink's :option:`--twitch-api-header` or :option:`--http-header` CLI arguments.

The value of the ``Authorization`` header must be in the format of ``OAuth YOUR_TOKEN``. Notice the space character in the
argument value, which requires quotation on command line shells:

.. code-block:: console

    $ streamlink "--twitch-api-header=Authorization=OAuth abcdefghijklmnopqrstuvwxyz0123" twitch.tv/CHANNEL best

The entire argument can optionally be added to Streamlink's (Twitch plugin specific)
:ref:`config file <cli/config:Plugin specific configuration file>`, which :ref:`doesn't require quotes <cli/config:Syntax>`:

.. code-block:: text

    twitch-api-header=Authorization=OAuth abcdefghijklmnopqrstuvwxyz0123


Embedded ads
------------

In 2019, Twitch started embedding ads directly into streams in addition to their regular advertisement program
on their website which can only overlay ads. While this may be an annoyance for people who are used to using ad-blocker
extensions in their web-browsers for blocking regular overlaying ads, applications like Streamlink face another problem,
namely stream discontinuities when there's a transition between the regular stream content and an ad or another follow-up ad.

Since Streamlink does only output a single progressive stream from reading Twitch's segmented HLS stream, ads can cause issues
in certain players, as the output is not a cohesively encoded stream of audio and video data anymore during an ad transition.
One of the problematic players is :ref:`VLC <players:Players>`, which is known to crash during these stream discontinuities in
certain cases.

**Streamlink will therefore automatically filter out ad segments and pause the stream output during ads**.
Prior releases between version ``1.1.0`` and ``7.5.0`` required the ``--twitch-disable-ads`` plugin argument, as filtering out
ads was deemed optional. Ad filtering became necessary when Twitch changed the stream's container format, to prevent playback
issues during stream discontinuities between the stream and ads.

Filtering out ads means that the stream output will be paused during that time, and the player will keep trying to read data
until the real stream becomes available again. The discontinuity when the output resumes is expected and can't be circumvented.
Players should be able to recover from this, though. A message with an expected advertisement time will be logged.

Completely preventing ads may be possible by :ref:`authenticating <cli/plugins/twitch:Authentication>` (Twitch Turbo)
or via special Twitch API request headers and/or parameters that modify the access token acquirement, if the community is aware
of such loop-holes. See :option:`--twitch-api-header` and :option:`--twitch-access-token-param`.


Client-integrity token
----------------------

In 2022, Twitch added client-integrity tokens to their web player when getting streaming access tokens. These client-integrity
tokens are calculated using sophisticated JavaScript code which is infeasible to re-implement. The goal is to prevent bots
and third party applications from accessing streams by determining whether the client is legit or not.

Client-integrity tokens were treated as an optional request parameter when getting streaming access tokens, but this changed
at the end of May in 2023 when Twitch made them a requirement for a week, which broke Streamlink's Twitch plugin (#5370).

Since the only sensible solution for Streamlink to calculate client-integrity tokens was using a web browser,
the :ref:`streamlink.webbrowser <api/webbrowser:Webbrowser>` API was implemented in ``6.0.0``, which requires
a Chromium-based web browser being installed on the user's system. See the :option:`--webbrowser` and related CLI arguments
for more details.

As long as client-integrity tokens are optional, Streamlink does not require the webbrowser API. If they are, or if the user
has set the :option:`--twitch-force-client-integrity` argument, then the token will be calculated once and then cached
for as long as it's valid. :option:`--twitch-purge-client-integrity` allows clearing the cached token.

If supported by the Chromium-based web browser and the environment Streamlink is run in, :option:`--webbrowser-headless`
allows hiding the web browser's window.


Low latency streaming
---------------------

Low latency streaming on Twitch can be enabled by setting the :option:`--twitch-low-latency` argument and (optionally)
configuring the :ref:`player <players:Players>` via :option:`--player-args` and reducing its own buffer to a bare minimum.

Setting :option:`--twitch-low-latency` will make Streamlink prefetch future HLS segments that are included in the HLS playlist
and which can be requested ahead of time. As soon as content becomes available, Streamlink can download it without having to
waste time on waiting for another HLS playlist refresh that might include new segments.

In addition to that, :option:`--twitch-low-latency` also reduces :option:`--hls-live-edge` to a value of at most ``2``, and it
also sets the :option:`--hls-segment-stream-data` argument.

:option:`--hls-live-edge` defines how many HLS segments Streamlink should stay behind the stream's live edge, so that it can
refresh playlists and download segments in time without causing buffering. Setting the value to ``1`` is not advised due to how
prefetching works.

:option:`--hls-segment-stream-data` lets Streamlink write the content of in-progress segment downloads to the output buffer
instead waiting for the entire segment to complete first before data gets written. Since HLS segments on Twitch have a playback
duration of 2 seconds for most streams, this further reduces output delay.

.. note::

    Low latency streams have to be enabled by the broadcasters on Twitch themselves. Regular streams can cause buffering issues
    with this option enabled due to the reduced :option:`--hls-live-edge` value.

    Unfortunately, there is no way to check whether a channel is streaming in low-latency mode before accessing the stream.

Player buffer tweaks
^^^^^^^^^^^^^^^^^^^^

Since players do have their own input buffer, depending on how much data the player wants to keep in its buffer before it starts
playing the stream, this can cause an unnecessary delay while trying to watch low latency streams. Player buffer sizes should
therefore be tweaked via the :option:`--player-args` CLI argument or via the player's configuration options.

The delay introduced by the player depends on the stream's bitrate and how much data is necessary to allow for a smooth playback
without causing any stuttering, e.g. when running out out available data.

Please refer to the player's own documentation for the available options.
