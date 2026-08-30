from streamlink.plugin.plugin import Plugin


# noinspection PyAbstractClass
class TestPluginMissing(Plugin):
    pass


# does not export plugin via __plugin__
# __plugin__ = TestPluginMissing
