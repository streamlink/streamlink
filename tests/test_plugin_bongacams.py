import unittest

from streamlink.plugins.bongacams import bongacams


class TestPluginBongacams(unittest.TestCase):
    def test_can_handle_url(self):
        """ positive cases """
        self.assertTrue(bongacams.can_handle_url('http://bongacams.com/1'))
        self.assertTrue(bongacams.can_handle_url('http://bongacams.com/0000000000test'))
        self.assertTrue(bongacams.can_handle_url('http://bongacams.com/_-_test_-'))
        self.assertTrue(bongacams.can_handle_url('http://bongacams.com/TEst'))
        self.assertTrue(bongacams.can_handle_url('http://xx.bongacams.com/1'))
        self.assertTrue(bongacams.can_handle_url('http://xx.bongacams.com/0000000000test'))
        self.assertTrue(bongacams.can_handle_url('http://xx.bongacams.com/_-_test_-'))
        self.assertTrue(bongacams.can_handle_url('http://xx.bongacams.com/TEst'))
        self.assertTrue(bongacams.can_handle_url('https://bongacams.com/1'))
        self.assertTrue(bongacams.can_handle_url('https://bongacams.com/0000000000test'))
        self.assertTrue(bongacams.can_handle_url('https://bongacams.com/_-_test_-'))
        self.assertTrue(bongacams.can_handle_url('https://bongacams.com/TEst'))
        self.assertTrue(bongacams.can_handle_url('https://xx.bongacams.com/1'))
        self.assertTrue(bongacams.can_handle_url('https://xx.bongacams.com/0000000000test'))
        self.assertTrue(bongacams.can_handle_url('https://xx.bongacams.com/_-_test_-'))
        self.assertTrue(bongacams.can_handle_url('https://xx.bongacams.com/TEst'))
        self.assertTrue(bongacams.can_handle_url('bongacams.com/1'))
        self.assertTrue(bongacams.can_handle_url('bongacams.com/0000000000test'))
        self.assertTrue(bongacams.can_handle_url('bongacams.com/_-_test_-'))
        self.assertTrue(bongacams.can_handle_url('bongacams.com/TEst'))
        self.assertTrue(bongacams.can_handle_url('xx.bongacams.com/1'))
        self.assertTrue(bongacams.can_handle_url('xx.bongacams.com/0000000000test'))
        self.assertTrue(bongacams.can_handle_url('xx.bongacams.com/_-_test_-'))
        self.assertTrue(bongacams.can_handle_url('xx.bongacams.com/TEst'))

        """ Negative cases """
        # invalid schema
        self.assertFalse(bongacams.can_handle_url("test://bongacams.com/test"))

        # invalid stream path
        self.assertFalse(bongacams.can_handle_url('http://bongacams.com/ '))
        self.assertFalse(bongacams.can_handle_url('http://bongacams.com/'))
        self.assertFalse(bongacams.can_handle_url('http://bongacams.com/\\'))
        self.assertFalse(bongacams.can_handle_url('http://bongacams.com/\test'))
        self.assertFalse(bongacams.can_handle_url('http://xx.bongacams.com/ '))
        self.assertFalse(bongacams.can_handle_url('http://xx.bongacams.com/'))
        self.assertFalse(bongacams.can_handle_url('http://xx.bongacams.com/\\'))
        self.assertFalse(bongacams.can_handle_url('http://xx.bongacams.com/\\test'))
        self.assertFalse(bongacams.can_handle_url('https://bongacams.com/ '))
        self.assertFalse(bongacams.can_handle_url('https://bongacams.com/'))
        self.assertFalse(bongacams.can_handle_url('https://bongacams.com/\\'))
        self.assertFalse(bongacams.can_handle_url('https://bongacams.com/\test'))
        self.assertFalse(bongacams.can_handle_url('https://xx.bongacams.com/ '))
        self.assertFalse(bongacams.can_handle_url('https://xx.bongacams.com/'))
        self.assertFalse(bongacams.can_handle_url('https://xx.bongacams.com/\\'))
        self.assertFalse(bongacams.can_handle_url('https://xx.bongacams.com/\test'))
        self.assertFalse(bongacams.can_handle_url('bongacams.com/ '))
        self.assertFalse(bongacams.can_handle_url('bongacams.com/'))
        self.assertFalse(bongacams.can_handle_url('bongacams.com/\\'))
        self.assertFalse(bongacams.can_handle_url('bongacams.com/\test'))
        self.assertFalse(bongacams.can_handle_url('xx.bongacams.com/ '))
        self.assertFalse(bongacams.can_handle_url('xx.bongacams.com/'))
        self.assertFalse(bongacams.can_handle_url('xx.bongacams.com/\\'))
        self.assertFalse(bongacams.can_handle_url('xx.bongacams.com/\test'))

        # invalid domain
        self.assertFalse(bongacams.can_handle_url('https:// /test'))
        self.assertFalse(bongacams.can_handle_url('https://xxx.bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('https://x.bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('https://x.bongacams/test'))
        self.assertFalse(bongacams.can_handle_url('https://bongacams.jp/test'))
        self.assertFalse(bongacams.can_handle_url('https://test.domain/test'))
        self.assertFalse(bongacams.can_handle_url('https://bongacams.co.uk/test'))

        # invalid separator
        self.assertFalse(bongacams.can_handle_url('http bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('https bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url(' bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('http//bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('https//bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('//bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('http:///bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('https:///bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url(':///bongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('httptestbongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('httpstestbongacams.com/test'))
        self.assertFalse(bongacams.can_handle_url('testbongacams.com/test'))


if __name__ == "__main__":
    unittest.main()
