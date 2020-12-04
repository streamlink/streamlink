from tests.plugin.testplugin import __plugin__ as TestPlugin


class TestPluginOverride(TestPlugin):
    @classmethod
    def bind(cls, *args, **kwargs):
        super().bind(*args, **kwargs)
        cls.module = "testplugin"


__plugin__ = TestPluginOverride
