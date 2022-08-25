from tests.plugin.testplugin import __plugin__ as TestPlugin


class TestPluginOverride(TestPlugin):
    pass


__plugin__ = TestPluginOverride
