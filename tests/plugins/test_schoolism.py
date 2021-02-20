import unittest

from streamlink.plugins.schoolism import Schoolism
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSchoolism(PluginCanHandleUrl):
    __plugin__ = Schoolism

    should_match = [
        'https://www.schoolism.com/watchLesson.php',
    ]

    should_not_match = [
        'https://www.schoolism.com',
    ]


class TestPluginSchoolism(unittest.TestCase):
    def test_playlist_parse_subs(self):
        with_subs = """var allVideos=[
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/44/2/part1.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Digital Painting - Lesson 2 - Part 1",playlistTitle:"Part 1",}],        subtitles: [{
                    "default": true,
                    kind: "subtitles", srclang: "en", label: "English",
                    src:  "https://s3.amazonaws.com/schoolism-encoded/44/subtitles/2/2-1.vtt",
                }],
                },
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/44/2/part2.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Digital Painting - Lesson 2 - Part 2",playlistTitle:"Part 2",}],        subtitles: [{
                    "default": true,
                    kind: "subtitles", srclang: "en", label: "English",
                    src:  "https://s3.amazonaws.com/schoolism-encoded/44/subtitles/2/2-2.vtt",
                }]
            }];
            """  # noqa: E501

        data = Schoolism.playlist_schema.validate(with_subs)

        self.assertIsNotNone(data)
        self.assertEqual(2, len(data))

    def test_playlist_parse(self):
        without_subs = """var allVideos=[
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/14/1/part1.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Gesture Drawing - Lesson 1 - Part 1",playlistTitle:"Part 1",}],},
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/14/1/part2.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Gesture Drawing - Lesson 1 - Part 2",playlistTitle:"Part 2",}]}
            ];
        """  # noqa: E501

        data = Schoolism.playlist_schema.validate(without_subs)

        self.assertIsNotNone(data)
        self.assertEqual(2, len(data))

    def test_playlist_parse_colon_in_title(self):
        colon_in_title = """var allVideos=[
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/52/1/part1.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Deconstructed: Drawing People - Lesson 1 - Part 1",playlistTitle:"Part 1",}],},
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/52/1/part2.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Deconstructed: Drawing People - Lesson 1 - Part 2",playlistTitle:"Part 2",}],},
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/52/1/part3.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Deconstructed: Drawing People - Lesson 1 - Part 3",playlistTitle:"Part 3",}],},
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/52/1/part4.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Deconstructed: Drawing People - Lesson 1 - Part 4",playlistTitle:"Part 4",}],},
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/52/1/part5.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Deconstructed: Drawing People - Lesson 1 - Part 5",playlistTitle:"Part 5",}],},
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/52/1/part6.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Deconstructed: Drawing People - Lesson 1 - Part 6",playlistTitle:"Part 6",}],},
            {sources:[{type:"application/x-mpegurl",src:"https://d8u31iyce9xic.cloudfront.net/52/1/part7.m3u8?Policy=TOKEN&Signature=TOKEN&Key-Pair-Id=TOKEN",title:"Deconstructed: Drawing People - Lesson 1 - Part 7",playlistTitle:"Part 7",}]}
            ];
        """  # noqa: E501

        data = Schoolism.playlist_schema.validate(colon_in_title)

        self.assertIsNotNone(data)
        self.assertEqual(7, len(data))
