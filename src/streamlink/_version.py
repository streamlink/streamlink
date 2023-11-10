# This module will get replaced by versioningit when building a source distribution
# and instead of trying to get the version string from git, a static version string will be set

def _get_version() -> str:
    """
    Get the current version from git in "editable" installs
    """
    from pathlib import Path  # noqa: PLC0415
    from versioningit import get_version  # noqa: PLC0415
    import streamlink  # noqa: PLC0415

    return get_version(project_dir=Path(streamlink.__file__).parents[2])


__version__ = _get_version()
