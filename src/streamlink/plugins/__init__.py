from streamlink.compat import deprecated


deprecated({
    "NoPluginError": (
        "streamlink.exceptions.NoPluginError",
        None,
        "Importing from streamlink.plugins.NoPluginError has been deprecated",
    ),
    "NoStreamsError": (
        "streamlink.exceptions.NoStreamsError",
        None,
        "Importing from streamlink.plugins.NoStreamsError has been deprecated",
    ),
    "PluginError": (
        "streamlink.exceptions.PluginError",
        None,
        "Importing from streamlink.plugins.PluginError has been deprecated",
    ),
    "Plugin": (
        "streamlink.plugin.plugin.Plugin",
        None,
        "Importing from streamlink.plugins.Plugin has been deprecated",
    ),
})


__all__ = ["Plugin", "PluginError", "NoStreamsError", "NoPluginError"]  # noqa: F822
