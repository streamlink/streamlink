import unittest

from streamlink.plugin.api.utils import itertags


class TestPluginApiUtils(unittest.TestCase):

    def test_itertags(self):
        # ('text', 'tag', 'attribute', 'list(result)')
        itertags_list = [
            (
                """
                <div id="video_box_wrap-123" class="video_box_wrap">
                  <div id="video_box_mobile_thumb" class="video_box_mobile_thumb"></div>
                  <video id="video_player" poster="" data-duration="0">
                    <source src="https://example.com/0/0.m3u8" type="application/vnd.apple.mpegurl" />
                    <div class="video_box_background" style="background-image"></div>
                    <div class="video_box_cant_play">ERROR</div>
                  </video>
                </div>
                """,
                "source", "src",
                ["https://example.com/0/0.m3u8"]
            ),
            (
                """
                 <div id="video_box_mobile_thumb" class="video_box_mobile_thumb" style=""></div>
                  <video id="video_player" data-duration="2239">
                    <source src="https://example.com/1/0.m3u8" type="application/vnd.apple.mpegurl" />
                    <source src="https://example.com/1/1080.mp4" type="video/mp4" />
                    <source src="https://example.com/1/720.mp4" type="video/mp4" />
                    <source src="https://example.com/1/480.mp4" type="video/mp4" />
                    <source src="https://example.com/1/360.mp4" type="video/mp4" />
                    <source src="https://example.com/1/240.mp4" type="video/mp4" />
                    <div class="video_box_background" style="background-image"></div>
                    <div class="video_box_cant_play">ERROR</div>
                  </video>
                </div>
                """,
                "source", "src",
                [
                    "https://example.com/1/0.m3u8",
                    "https://example.com/1/1080.mp4",
                    "https://example.com/1/720.mp4",
                    "https://example.com/1/480.mp4",
                    "https://example.com/1/360.mp4",
                    "https://example.com/1/240.mp4",
                ]
            ),
            (
                """
                <div class="video_box_wrap">
                <iframe id="video_player" preventhide="1" type="text/html"
                src="//foo.bar/play/embed/13"
                scrolling="no" frameborder="0" allow="autoplay"></iframe></div>
                """,
                "iframe", "src",
                [
                    "//foo.bar/play/embed/13"
                ]
            )
        ]

        for text, tag, attribute, result in itertags_list:
            _i = itertags(text, tag)
            count = 0
            for _tag in _i:
                self.assertEqual(_tag.attributes[attribute], result[count])
                count += 1
