from pathlib import Path


def core() -> str:
    """
    Read the contents of the JavaScript core solver bundle as string.
    """
    return (Path(__file__).parent / "core.min.js").read_text(encoding="utf-8")


def lib() -> str:
    """
    Read the contents of the JavaScript library solver bundle as string.
    """
    return (Path(__file__).parent / "lib.min.js").read_text(encoding="utf-8")
