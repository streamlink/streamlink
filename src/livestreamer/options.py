options = {
    "rtmpdump": None,
    "errorlog": False,
    "jtvcookie": None
}

def set(key, value):
    options[key] = value

def get(key):
    if key in options:
        return options[key]

__all__ = ["get", "set"]
