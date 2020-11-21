import os
import warnings

import pytest


def catch_warnings(record=False, module=None):
    def _catch_warnings_wrapper(f):
        def _catch_warnings(*args, **kwargs):
            with warnings.catch_warnings(record=True, module=module) as w:
                if record:
                    return f(*(args + (w,)), **kwargs)
                else:
                    return f(*args, **kwargs)

        return _catch_warnings

    return _catch_warnings_wrapper


windows_only = pytest.mark.skipif(os.name != "nt", reason="test only applicable on Window")
posix_only = pytest.mark.skipif(os.name != "posix", reason="test only applicable on a POSIX OS")


__all__ = ['catch_warnings', 'windows_only', 'posix_only']
