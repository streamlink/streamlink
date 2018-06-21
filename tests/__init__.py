import warnings


def catch_warnings(record=False, module=None):
    def _catch_warnings_wrapper(f):
        def _catch_warnings(*args, **kwargs):
            with warnings.catch_warnings(record=True, module=module) as w:
                if record:
                    return f(*(args + (w, )), **kwargs)
                else:
                    return f(*args, **kwargs)
        return _catch_warnings

    return _catch_warnings_wrapper


__all__ = ['ignore_warnings']
