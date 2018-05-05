from collections import OrderedDict


class Options(object):
    def __init__(self, defaults=None):
        if not defaults:
            defaults = {}

        self.defaults = defaults
        self.options = defaults.copy()

    def set(self, key, value):
        self.options[key] = value

    def get(self, key):
        if key in self.options:
            return self.options[key]


class Argument(object):
    """
        :class:`Argument` accepts most of the same parameters as :func:`ArgumentParser.add_argument`,
        except requires is a special case as in this case it is only enforced if the plugin is in use.
        In addition the name parameter is the name relative to the plugin eg. username, password, etc.

    """
    def __init__(self, name, required=False, requires=None, prompt=None, sensitive=False, argument_name=None,
                 dest=None, **options):
        """
        :param name: name of the argument, without -- or plugin name prefixes, eg. ``"password"``, ``"mux-subtitles"``, etc.
        :param required (bool): if the argument is required for the plugin
        :param requires: list of the arguments which this argument requires, eg ``["password"]``
        :param prompt: if the argument is required and not given, this prompt will show at run time
        :param sensitive (bool): if the argument is sensitive (passwords, etc) and should be masked in logs and if
                              prompted use askpass
        :param argument_name:
        :param option_name:
        :param options: arguments passed to :func:`ArgumentParser.add_argument`, excluding requires, and dest
        """
        self.required = required
        self.name = name
        self.options = options
        self._argument_name = argument_name  # override the cli argument name
        self._dest = dest  # override for the plugin option name
        self.requires = requires and (list(requires) if isinstance(requires, (list, tuple)) else [requires]) or []
        self.prompt = prompt
        self.sensitive = sensitive

    def _name(self, plugin):
        return self._argument_name or "{0}-{1}".format(plugin, self.name).strip("-")

    def argument_name(self, plugin):
        return "--" + self._name(plugin)

    def namespace_dest(self, plugin):
        return self._name(plugin).replace('-', '_')

    @property
    def dest(self):
        return self._dest or self.name.replace("-", "_")


class Arguments(object):
    """
    Provides a wrapper around a list of :class:`Argument`. For example

    .. code-block:: python

        class PluginExample(Plugin):
            arguments = PluginArguments(
                PluginArgument("username",
                               help="The username for your account.",
                               metavar="EMAIL",
                               requires=["password"]),  // requires the password too
                PluginArgument("password",
                               sensitive=True,  // should be masked in logs, etc.
                               help="The password for your account.",
                               metavar="PASSWORD")
            )

    This will add the ``--plugin-username`` and ``--plugin-password`` arguments to the CLI
    (assuming the plugin module is ``plugin``).

    """
    def __init__(self, *args):
        self.arguments = OrderedDict((arg.name, arg) for arg in args)

    def __iter__(self):
        return iter(self.arguments.values())

    def get(self, name):
        return self.arguments.get(name)

    def requires(self, name):
        """
        Find all the arguments required by name

        :param name: name of the argument the find the dependencies

        :return: list of dependant arguments
        """
        results = set([name])
        argument = self.get(name)
        for reqname in argument.requires:
            required = self.get(reqname)
            if not required:
                raise KeyError("{0} is not a valid argument for this plugin".format(reqname))

            if required.name in results:
                raise RuntimeError("cycle detected in plugin argument config")
            results.add(required.name)
            yield required

            for r in self.requires(required.name):
                if r.name in results:
                    raise RuntimeError("cycle detected in plugin argument config")
                results.add(r.name)
                yield r


__all__ = ["Options", "Arguments", "Argument"]
