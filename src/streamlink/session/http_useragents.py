# ruff: file-ignore[line-too-long]

ANDROID = "Mozilla/5.0 (Linux; Android 17) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.8037.93 Mobile Safari/537.36"
CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
CHROME_OS = "Mozilla/5.0 (X11; CrOS x86_64 16765.51.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.7977.132 Safari/537.36"
FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0"
IE_11 = "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0 Mobile/15E148 Safari/604.1"
OPERA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 OPR/137.0.0.0"
SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_8_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/27.0 Safari/605.1.15"

ANDROID_VERSION = (17,)
CHROME_VERSION = (154, 0, 8037, 94)
CHROME_OS_VERSION = (152, 0, 7977, 132)
FIREFOX_VERSION = (157, 0)
IE_11_VERSION = (11,)
IPHONE_VERSION = (18, 7, 8)
OPERA_VERSION = (137, 0, 6022, 0)
SAFARI_VERSION = (27,)

# Backwards compatibility
EDGE = CHROME
FIREFOX_MAC = FIREFOX
IE_6 = IE_7 = IE_8 = IE_9 = IE_11
IPHONE_6 = IPAD = IPHONE
SAFARI_7 = SAFARI_8 = SAFARI
WINDOWS_PHONE_8 = ANDROID

DEFAULT = FIREFOX
