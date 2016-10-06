.. _plugin_matrix:


Plugins
=======

This is a list of the currently built in plugins and what URLs and features
they support. Streamlink's primary focus is live streams, so VOD support
is limited.


=================== ==================== ===== ===== ===========================
Name                URL(s)               Live  VOD   Notes
=================== ==================== ===== ===== ===========================
afreeca             afreecatv.com        Yes   No
afreecatv           afreeca.tv           Yes   No
aftonbladet         aftonbladet.se       Yes   Yes
alieztv             aliez.tv             Yes   Yes
antenna             antenna.gr           --    Yes
ard_live            live.daserste.de     Yes   --    Streams may be geo-restricted to Germany.
ard_mediathek       ardmediathek.de      Yes   Yes   Streams may be geo-restricted to Germany.
artetv              arte.tv              Yes   Yes
azubutv             azubu.tv             Yes   No
bambuser            bambuser.com         Yes   Yes
beam                beam.pro             Yes   No
beattv              be-at.tv             Yes   Yes   Playlist not implemented yet.
bilibili            live.bilibili.com    Yes   ?
bliptv              blip.tv              --    Yes
chaturbate          chaturbate.com       Yes   No
connectcast         connectcast.tv       Yes   Yes
crunchyroll         crunchyroll.com      --    Yes
cybergame           cybergame.tv         Yes   Yes
dailymotion         dailymotion.com      Yes   Yes
disney_de           - video.disney.de    Yes   Yes   Streams may be geo-restricted to Germany.
                    - disneychannel.de
dmcloud             api.dmcloud.net      Yes   --
dommune             dommune.com          Yes   --
douyutv             douyutv.com          Yes   --
dplay               - dplay.se           --    Yes   Streams may be geo-restricted.
                                                     Only non-premium streams currently supported.
                    - dplay.no
                    - dplay.dk
drdk                dr.dk                Yes   Yes   Streams may be geo-restricted to Denmark.
euronews            euronews.com         Yes   No
expressen           expressen.se         Yes   Yes
filmon              filmon.com           Yes   Yes   Only SD quality streams.
filmon_us           filmon.us            Yes   Yes
furstream           furstre.am           Yes   No
gaminglive          gaminglive.tv        Yes   Yes
gomexp              gomexp.com           Yes   No
goodgame            goodgame.ru          Yes   No    Only HLS streams are available.
hitbox              hitbox.tv            Yes   Yes
itvplayer           itv.com/itvplayer    Yes   Yes   Streams may be geo-restricted to Great Britain.
letontv             leton.tv             Yes   --
livecoding          livecoding.tv        Yes   --
livestation         livestation.com      Yes   --
livestream          new.livestream.com   Yes   --
media_ccc_de        - media.ccc.de       Yes   Yes   Only mp4 and HLS are supported.
                    - streaming... [4]_
mediaklikk          mediaklikk.hu        Yes   No    Streams may be geo-restricted to Hungary.
meerkat             meerkatapp.co        Yes   --
mips                mips.tv              Yes   --    Requires rtmpdump with K-S-V patches.
mlgtv               mlg.tv               Yes   --
nhkworld            nhk.or.jp/nhkworld   Yes   No
nos                 nos.nl               Yes   Yes   Streams may be geo-restricted to Netherlands.
npo                 npo.nl               Yes   Yes   Streams may be geo-restricted to Netherlands.
nrk                 - tv.nrk.no          Yes   Yes   Streams may be geo-restricted to Norway.
                    - radio.nrk.no
oldlivestream       original.liv... [3]_ Yes   No    Only mobile streams are supported.
openrectv           openrec.tv           Yes   Yes
orf_tvthek          tvthek.orf.at        Yes   Yes
pandatv             panda.tv             Yes   ?
periscope           periscope.tv         Yes   Yes   Replay/VOD is supported.
picarto             picarto.tv           Yes   --
rtlxl               rtlxl.nl             No    Yes   Streams may be geo-restriced to The Netherlands. Livestreams not supported.
rtve                rtve.es              Yes   No
ruv                 ruv.is               Yes   Yes   Streams may be geo-restricted to Iceland.
seemeplay           seemeplay.ru         Yes   Yes
servustv            servustv.com         ?     ?
speedrunslive       speedrunslive.com    Yes   --    URL forwarder to Twitch channels.
sportschau          sportschau.de        Yes   No
ssh101              ssh101.com           Yes   No
streamboat          streamboat.tv        Yes   No
streamingvi... [1]_ streamingvid... [2]_ Yes   --    RTMP streams requires rtmpdump with
                                                     K-S-V patches.
streamlive          streamlive.to        Yes   --
streamme            stream.me            Yes   --
streamupcom         streamup.com         Yes   --
svtplay             - svtplay.se         Yes   Yes   Streams may be geo-restricted to Sweden.
                    - svtflow.se
                    - oppetarkiv.se
tga                 - star.plu.cn        Yes   No
                    - star.tga.plu.cn
tv3cat              tv3.cat              Yes   Yes   Streams may be geo-restricted to Spain.
tv4play             - tv4play.se         Yes   Yes   Streams may be geo-restricted to Sweden.
                                                     Only non-premium streams currently supported.
                    - fotbollskanalen.se
tvcatchup           - tvcatchup.com      Yes   No    Streams may be geo-restricted to Great Britain.
tvplayer            tvplayer.com         Yes   No    Streams may be geo-restricted to Great Britain. Premium streams are not supported.
twitch              twitch.tv            Yes   Yes   Possible to authenticate for access to
                                                     subscription streams.
ustreamtv           ustream.tv           Yes   Yes   Currently broken.
vaughnlive          - vaughnlive.tv      Yes   --
                    - breakers.tv
                    - instagib.tv
                    - vapers.tv
veetle              veetle.com           Yes   Yes
vgtv                vgtv.no              Yes   Yes
viagame             viagame.com
viasat              - tv3play.se         Yes   Yes   Streams may be geo-restricted.
                    - tv3play.no
                    - tv3play.dk
                    - tv3play.ee
                    - tv3play.lt
                    - tv3play.lv
                    - tv6play.se
                    - tv6play.no
                    - tv8play.se
                    - tv10play.se
                    - viasat4play.no
                    - play.tv3.lt
                    - juicyplay.se
vidio               vidio.com            Yes   Yes
wattv               wat.tv               --    Yes
weeb                weeb.tv              Yes   --    Requires rtmpdump with K-S-V patches.
younow              younow.com           Yes   --
youtube             - youtube.com        Yes   Yes   Protected videos are not supported.
                    - youtu.be
zdf_mediathek       zdf.de               Yes   Yes
=================== ==================== ===== ===== ===========================


.. [1] streamingvideoprovider
.. [2] streamingvideoprovider.co.uk
.. [3] original.livestream.com
.. [4] streaming.media.ccc.de
