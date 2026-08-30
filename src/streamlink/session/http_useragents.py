# ruff: file-ignore[line-too-long]

ANDROID = "Mozilla/5.0 (Linux; Android 17) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.187 Mobile Safari/537.36"
CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
CHROME_OS = "Mozilla/5.0 (X11; CrOS x86_64 16700.46.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.150 Safari/537.36"
FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0"
IE_11 = "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1"
OPERA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 OPR/133.0.0.0"
SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_7_8) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15"

ANDROID_VERSION = (17,)
CHROME_VERSION = (150, 0, 7871, 188)
CHROME_OS_VERSION = (150, 0, 7871, 150)
FIREFOX_VERSION = (153, 0, 1)
IE_11_VERSION = (11,)
IPHONE_VERSION = (18, 7, 8)
OPERA_VERSION = (133, 0, 5932, 85)
SAFARI_VERSION = (26,)

# Backwards compatibility
EDGE = CHROME
FIREFOX_MAC = FIREFOX
IE_6 = IE_7 = IE_8 = IE_9 = IE_11
IPHONE_6 = IPAD = IPHONE
SAFARI_7 = SAFARI_8 = SAFARI
WINDOWS_PHONE_8 = ANDROID

DEFAULT = FIREFOX
