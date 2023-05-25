from streamlink.plugins.ustvnow import USTVNow
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlUSTVNow(PluginCanHandleUrl):
    __plugin__ = USTVNow

    should_match = [
        "http://www.ustvnow.com/live/foo/-65",
    ]


class TestPluginUSTVNow:
    def test_encrypt_data(self):
        key = "80035ad42d7d-bb08-7a14-f726-78403b29"
        iv = "3157b5680927cc4a"

        assert USTVNow.encrypt_data(
            b'{"login_id":"test@test.com","login_key":"testtest1234","login_mode":"1","manufacturer":"123"}',
            key,
            iv,
        ) == (
            b"uawIc5n+TnmsmR+aP2iEDKG/eMKji6EKzjI4mE+zMhlyCbHm7K4hz7IDJDWwM3aE+Ro4ydSsgJf4ZInnoW6gqvXvG0qB"
            + b"/J2WJeypTSt4W124zkJpvfoJJmGAvBg2t0HT"
        )

    def test_decrypt_data(self):
        key = "80035ad42d7d-bb08-7a14-f726-78403b29"
        iv = "3157b5680927cc4a"

        assert USTVNow.decrypt_data(
            b"KcRLETVAmHlosM0OyUd5hdTQ6WhBRTe/YRAHiLJWrzf94OLkSueXTtQ9QZ1fjOLCbpX2qteEPUWVnzvvSgVDkQmRUttN"
            + b"/royoxW2aL0gYQSoH1NWoDV8sIgvS5vDiQ85",
            key,
            iv,
        ) == b'{"status":false,"error":{"code":-2,"type":"","message":"Invalid credentials.","details":{}}}'
