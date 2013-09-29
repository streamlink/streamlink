from livestreamer.stream import HTTPStream

def get_streams(session):
    return dict(support=HTTPStream(session, "http://test.se/support"))
