import base64

from streamlink.utils.crypto import decrypt_openssl, evp_bytestokey


class TestUtil:
    def test_evp_bytestokey(self):
        assert evp_bytestokey(b"hello", b"", 16, 16) == (
            b"]A@*\xbcK*v\xb9q\x9d\x91\x10\x17\xc5\x92",
            b"(\xb4n\xd3\xc1\x11\xe8Q\x02\x90\x9b\x1c\xfbP\xea\x0f",
        )

    def test_decrpyt(self):
        # data generated with:
        #   echo "this is a test" | openssl enc -aes-256-cbc -pass pass:"streamlink" -base64
        data = base64.b64decode("U2FsdGVkX18nVyJ6Y+ksOASMSHKuRoQ9b4DKHuPbyQc=")
        assert decrypt_openssl(data, b"streamlink") == b"this is a test\n"
