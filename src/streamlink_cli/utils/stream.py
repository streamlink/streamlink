def stream_to_url(stream):
    try:
        return stream.to_url()
    except TypeError:
        return None
