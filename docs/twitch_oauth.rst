.. _twitch_oauth:

Twitch OAuth authentication
===========================


.. raw:: html

    <script type="text/javascript">
        $(function() {
            var el = $(".highlight");
            var params = (window.location.hash.substr(1)).split("&");

            for (i = 0; i < params.length; i++) {
                var keyval = params[i].split("=");

                if (keyval[0] == "access_token")
                {
                    el.html('<pre>twitch-oauth-token<span class="o">=</span>' + keyval[1] + '</pre>');
                }
            }
        });
    </script>

    <div class="oauth"></div>


You successfully authenticated Livestreamer with Twitch.

Paste this into your :ref:`configuration file <cli-livestreamerrc>`:

.. code-block:: bash

    twitch-oauth-token=

