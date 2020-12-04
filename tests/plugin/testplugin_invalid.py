class TestPluginInvalid:
    pass


# does not inherit from streamlink.plugin.plugin.Plugin
__plugin__ = TestPluginInvalid
