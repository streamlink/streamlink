from streamlink.stream.segmented.segmented import log


def test_logger_name():
    assert log.name == "streamlink.stream.segmented"
