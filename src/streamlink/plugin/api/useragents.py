ANDROID = ("Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36")
CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36")
CHROME_OS = ("Mozilla/5.0 (X11; CrOS armv7l 4537.56.0) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.38 Safari/537.36")
IE_11 = "Mozilla/5.0 (MSIE 10.0; Windows NT 6.1; Trident/5.0)"
IE_6 = "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; WOW64; Trident/4.0; SLCC1)"
IE_7 = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; WOW64; Trident/4.0; SLCC1)"
IE_8 = "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; WOW64; Trident/4.0; SLCC1)"
IE_9 = "Mozilla/5.0 (MSIE 9.0; Windows NT 6.1; Trident/5.0)"
IPHONE_6 = ("Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) "
            "AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25")
IPAD = ("Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) "
        "AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25")
WINDOWS_PHONE_8 = ("Mozilla/5.0 (compatible; MSIE 10.0; Windows Phone 8.0; "
                   "Trident/6.0; IEMobile/10.0; ARM; Touch; NOKIA; Lumia 920)")
SAFARI_8 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) "
            "AppleWebKit/600.7.12 (KHTML, like Gecko) Version/8.0.7 Safari/600.7.12")
SAFARI_7 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) "
            "AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A")
FIREFOX = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:52.0) Gecko/20100101 Firefox/52.0"
FIREFOX_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0"
OPERA = "Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14"


def random_agent():

    import random
    from streamlink.compat import range

    BR_VERS = [
        ['%s.0' % i for i in range(18, 50)],
        ['37.0.2062.103', '37.0.2062.120', '37.0.2062.124', '38.0.2125.101', '38.0.2125.104', '38.0.2125.111',
         '39.0.2171.71', '39.0.2171.95', '39.0.2171.99', '40.0.2214.93', '40.0.2214.111', '40.0.2214.115',
         '42.0.2311.90', '42.0.2311.135', '42.0.2311.152', '43.0.2357.81', '43.0.2357.124', '44.0.2403.155',
         '44.0.2403.157', '45.0.2454.101', '45.0.2454.85', '46.0.2490.71', '46.0.2490.80', '46.0.2490.86',
         '47.0.2526.73', '47.0.2526.80', '48.0.2564.116', '49.0.2623.112', '50.0.2661.86', '51.0.2704.103',
         '52.0.2743.116', '53.0.2785.143', '54.0.2840.71', '61.0.3163.100'],
        ['11.0'],
        ['8.0', '9.0', '10.0', '10.6']
    ]

    WIN_VERS = [
        'Windows NT 10.0', 'Windows NT 7.0', 'Windows NT 6.3', 'Windows NT 6.2', 'Windows NT 6.1', 'Windows NT 6.0',
        'Windows NT 5.1', 'Windows NT 5.0'
    ]

    FEATURES = ['; WOW64', '; Win64; IA64', '; Win64; x64', '']

    RAND_UAS = ['Mozilla/5.0 ({win_ver}{feature}; rv:{br_ver}) Gecko/20100101 Firefox/{br_ver}',
                'Mozilla/5.0 ({win_ver}{feature}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{br_ver} Safari/537.36',
                'Mozilla/5.0 ({win_ver}{feature}; Trident/7.0; rv:{br_ver}) like Gecko',
                'Mozilla/5.0 (compatible; MSIE {br_ver}; {win_ver}{feature}; Trident/6.0)']

    index = random.randrange(len(RAND_UAS))

    return RAND_UAS[
        index
    ].format(
        win_ver=random.choice(WIN_VERS), feature=random.choice(FEATURES), br_ver=random.choice(BR_VERS[index])
    )
