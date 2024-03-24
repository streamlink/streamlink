from streamlink.compat import deprecated
from streamlink.session.http import HTTPSession, TLSNoDHAdapter, TLSSecLevel1Adapter


deprecated({
    "HTTPSession": (None, HTTPSession, None),
    "TLSNoDHAdapter": (None, TLSNoDHAdapter, None),
    "TLSSecLevel1Adapter": (None, TLSSecLevel1Adapter, None),
})
