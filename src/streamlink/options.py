from collections import OrderedDict


def _normalise_option_name(name):
    return name.replace('-', '_')


def _normalise_argument_name(name):
    return name.replace('_', '-').strip("-")


class Options:
    """
    For storing options to be used by plugins, with default values.

    Note: Option names are normalised by replacing "-" with "_", this means that the keys
    ``example-one`` and ``example_one`` are equivalent.
    """
    def __init__(self, defaults=None):
        if not defaults:
            defaults = {}

        self.defaults = self._normalise_dict(defaults)
        self.options = self.defaults.copy()

    @classmethod
    def _normalise_dict(cls, src):
        dest = {}
        for key, value in src.items():
            dest[_normalise_option_name(key)] = value
        return dest

    def set(self, key, value):
        self.options[_normalise_option_name(key)] = value

    def get(self, key):
        key = _normalise_option_name(key)
        if key in self.options:
            return self.options[key]

    def update(self, options):
        for key, value in options.items():
            self.set(key, value)


class Argument:
    """
        :class:`Argument` accepts most of the same parameters as :func:`ArgumentParser.add_argument`,
        except requires is a special case as in this case it is only enforced if the plugin is in use.
        In addition the name parameter is the name relative to the plugin eg. username, password, etc.


    """
    def __init__(self, name, required=False, requires=None, prompt=None, sensitive=False, argument_name=None,
                 dest=None, is_global=False, **options):
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
        self._default = options.get("default")
        self.is_global = is_global

    def _name(self, plugin):
        return self._argument_name or _normalise_argument_name("{0}-{1}".format(plugin, self.name))

    def argument_name(self, plugin):
        return f"--{self.name if self.is_global else self._name(plugin)}"

    def namespace_dest(self, plugin):
        return _normalise_option_name(self._name(plugin))

    @property
    def dest(self):
        return self._dest or _normalise_option_name(self.name)

    @property
    def default(self):  # read-only
        return self._default


class Arguments:
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
        results = {name}
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
