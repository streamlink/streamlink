from streamlink.plugins.streann import Streann
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlStreann(PluginCanHandleUrl):
    __plugin__ = Streann

    should_match = [
        # ott.streann.com
        "https://ott.streann.com/streaming/player.html?U2FsdGVkX1/PAwXdSYuiw+o5BxSoG10K8ShiKMDOOUEuoYiQxiZlD0gg7y+Ij07/OaI9TWk+"
        + "MHp40Fx4jrOv304Z+PZwLqGJgs+b0xsnfZJMpx+UmYnjys1rzTZ8UeztNjDeYEElKdaHHGkv0HFcGBGWjyWOvQuCbjGyr4dtzLyaChewqR9lNCuil/HO"
        + "MiL/eYtEMEPVjMdeUFilb5GSVdIyeunr+JnI1tvdPC5ow3rx3NWjbqIHd13qWVSnaZSl/UZ0BDmWBf+Vr+3pPAd1Mg3y01mKaYZywOxRduBW2HZwoLQe"
        + "2Lok5Z/q4aJHO02ZESqEPLRKkEqMntuuqGfy1g==",
        "https://ott.streann.com/s-secure/player.html?U2FsdGVkX19Z8gO/ThCsK3I1DTIdVzIGRKiJP36DEx2K1n9HeXKV4nmJrKptTZRlTmM4KTxC/"
        + "Mi5k3kWEsC1pr9QWmQJzKAfGdROMWB6voarQ1UQqe8IMDiibG+lcNTggCIkAS8a+99Kbe/C1W++YEP+BCBC/8Ss2RYIhNyVdqjUtqvv4Exk6l1gJDWNH"
        + "c6b5P51020dUrkuJCgEJCbJBE/MYFuC5xlhmzf6kcN5GlBrTuwyHYBkkVi1nvjOm1QS0iQw36UgJx9JS3DDTf7BzlAimLV5M1rXS/ME3XpllejHV0aL3"
        + "sghCBzc4f4AAz1IoTsl4qEamWBxyfy2kdNJRQ==",
        # URL with iframe
        "https://centroecuador.ec/tv-radio/",
        "https://crc.cr/estaciones/crc-89-1/",
        "https://columnaestilos.com/",
        "https://crc.cr/estaciones/azul-999/",
        "https://evtv.online/noticias-de-venezuela/",
        "https://telecuracao.com/",
    ]

    should_not_match = [
        "https://ott.streann.com",
    ]
