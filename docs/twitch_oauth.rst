.. _twitch_oauth:

Twitch OAuth authentication
===========================


.. raw:: html

    <!-- Some themes include jquery after our code... -->
    <script type="text/javascript" src="_static/jquery.js"></script>
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


You successfully authenticated Streamlink with Twitch.

Paste this into your :ref:`configuration file <cli-streamlinkrc>`:

.. code-block:: bash

    twitch-oauth-token=
