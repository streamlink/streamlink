def stream_to_url(stream):
    stream_type = type(stream).shortname()

    if stream_type in ("hls", "http"):
        url = stream.url

    elif stream_type == "rtmp":
        params = [stream.params.pop("rtmp", "")]
        stream_params = dict(stream.params)

        if "swfVfy" in stream.params:
            stream_params["swfUrl"] = stream.params["swfVfy"]
            stream_params["swfVfy"] = True

        if "swfhash" in stream.params:
            stream_params["swfVfy"] = True
            stream_params.pop("swfhash", None)
            stream_params.pop("swfsize", None)

        for key, value in stream_params.items():
            if isinstance(value, bool):
                value = str(int(value))

            # librtmp expects some characters to be escaped
            value = value.replace("\\", "\\5c")
            value = value.replace(" ", "\\20")
            value = value.replace('"', "\\22")

            params.append("{0}={1}".format(key, value))

        url = " ".join(params)

    else:
        url = None

    return url
