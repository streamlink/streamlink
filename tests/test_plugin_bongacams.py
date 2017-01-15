import unittest

from streamlink.plugins.bongacams import bongacams


class TestPluginBongacams(unittest.TestCase):
    def test_can_handle_url(self):
        valid_sep = '://'
        valid_domains = ['bongacams.com', 'xx.bongacams.com']
        valid_schemes = ['http', 'https', '']
        valid_stream_paths = ['1', '0000000000test', '_-_test_-', 'TEst']

        non_valid_seps = [' ', '//', ':///', 'test']
        non_valid_domains = [' ', 'xxx.bongacams.com', 'x.bongacams.com', 'x.bongacams',
                             'bongacams.jp', 'test.domain', 'bongacams.co.uk']
        non_valid_stream_paths = [' ', '', '\\', '\\test', '|test']

        # {schema}{sep}{domain}/{stream_path}
        url = "{0}{1}{2}/{3}"

        """ Positive cases """
        for schema in valid_schemes:
            for domain in valid_domains:
                for stream_path in valid_stream_paths:
                    sep = valid_sep if schema else ''
                    _url = url.format(schema, sep, domain, stream_path)
                    self.assertTrue(bongacams.can_handle_url(_url), msg=_url)

        """ Negative cases """
        # invalid schema
        self.assertFalse(bongacams.can_handle_url("test://bongacams.com/test"))

        # invalid stream path
        for schema in valid_schemes:
            for domain in valid_domains:
                for stream_path in non_valid_stream_paths:
                    sep = valid_sep if schema else ''
                    _url = url.format(schema, sep, domain, stream_path)
                    self.assertFalse(bongacams.can_handle_url(_url), msg=_url)

        # invalid domain
        for domain in non_valid_domains:
            _url = url.format('https', valid_sep, domain, 'test')
            self.assertFalse(bongacams.can_handle_url(_url), msg=_url)

        # invalid separator
        for sep in non_valid_seps:
            for schema in valid_schemes:
                _url = url.format(schema, sep, 'bongacams.com', 'test')
                self.assertFalse(bongacams.can_handle_url(_url), msg=_url)


if __name__ == "__main__":
    unittest.main()
