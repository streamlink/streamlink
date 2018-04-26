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
    def __init__(self, name, required=False, name_override=None, requires=None, prompt=None, sensitive=False, **options):
        self.required = required
        self.name = name
        self.options = options
        self._name_override = name_override
        self.requires = requires and (list(requires) if isinstance(requires, (list, tuple)) else [requires]) or []
        self.prompt = prompt
        self.sensitive = sensitive

    def _name(self, plugin):
        return self._name_override or "{0}-{1}".format(plugin, self.name).strip("-")

    def argument_name(self, plugin):
        return "--" + self._name(plugin)

    def option_name(self, plugin):
        return self._name(plugin).replace('-', '_')


class Arguments(object):
    def __init__(self, *args):
        self.arguments = OrderedDict((arg.name, arg) for arg in args)

    def __iter__(self):
        return iter(self.arguments.values())

    def get(self, name):
        return self.arguments.get(name)

    def requires(self, name):
        """
        Find all the arguments required by name
        :param name:
        :return:
        """
        results = set([name])
        argument = self.get(name)
        for reqname in argument.requires:
            required = self.get(reqname)
            if not required:
                raise KeyError("{0} is not a valid argument for this plugin".format(reqname))

            if required.name in results:
                raise RecursionError("cycle detected in plugin argument config")
            results.add(required.name)
            yield required

            for r in self.requires(required.name):
                if r.name in results:
                    raise RecursionError("cycle detected in plugin argument config")
                results.add(r.name)
                yield r


__all__ = ["Options", "Arguments", "Argument"]
