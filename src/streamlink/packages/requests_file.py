"""
Copyright 2015 Red Hat, Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from io import BytesIO

import sys
from requests.adapters import BaseAdapter
from requests.compat import urlparse, unquote, urljoin
from requests import Response, codes
import errno
import os
import os.path
import stat
import locale
import io

from streamlink.compat import is_win32


class FileAdapter(BaseAdapter):
    def send(self, request, **kwargs):
        """ Wraps a file, described in request, in a Response object.

            :param request: The PreparedRequest` being "sent".
            :returns: a Response object containing the file
        """

        # Check that the method makes sense. Only support GET
        if request.method not in ("GET", "HEAD"):
            raise ValueError("Invalid request method %s" % request.method)

        # Parse the URL
        url_parts = urlparse(request.url)

        # Make the Windows URLs slightly nicer
        if is_win32 and url_parts.netloc.endswith(":"):
            url_parts = url_parts._replace(path="/" + url_parts.netloc + url_parts.path, netloc='')

        # Reject URLs with a hostname component
        if url_parts.netloc and url_parts.netloc not in ("localhost", ".", "..", "-"):
            raise ValueError("file: URLs with hostname components are not permitted")

        # If the path is relative update it to be absolute
        if url_parts.netloc in (".", ".."):
            pwd = os.path.abspath(url_parts.netloc).replace(os.sep, "/") + "/"
            if is_win32:
                # prefix the path with a / in Windows
                pwd = "/" + pwd
            url_parts = url_parts._replace(path=urljoin(pwd, url_parts.path.lstrip("/")))

        resp = Response()
        resp.url = request.url

        # Open the file, translate certain errors into HTTP responses
        # Use urllib's unquote to translate percent escapes into whatever
        # they actually need to be
        try:
            # If the netloc is - then read from stdin
            if url_parts.netloc == "-":
                resp.raw = sys.stdin.buffer
                # make a fake response URL, the current directory
                resp.url = "file://" + os.path.abspath(".").replace(os.sep, "/") + "/"
            else:
                # Split the path on / (the URL directory separator) and decode any
                # % escapes in the parts
                path_parts = [unquote(p) for p in url_parts.path.split('/')]

                # Strip out the leading empty parts created from the leading /'s
                while path_parts and not path_parts[0]:
                    path_parts.pop(0)

                # If os.sep is in any of the parts, someone fed us some shenanigans.
                # Treat is like a missing file.
                if any(os.sep in p for p in path_parts):
                    raise IOError(errno.ENOENT, os.strerror(errno.ENOENT))

                # Look for a drive component. If one is present, store it separately
                # so that a directory separator can correctly be added to the real
                # path, and remove any empty path parts between the drive and the path.
                # Assume that a part ending with : or | (legacy) is a drive.
                if path_parts and (path_parts[0].endswith('|') or path_parts[0].endswith(':')):
                    path_drive = path_parts.pop(0)
                    if path_drive.endswith('|'):
                        path_drive = path_drive[:-1] + ':'

                    while path_parts and not path_parts[0]:
                        path_parts.pop(0)
                else:
                    path_drive = ''

                # Try to put the path back together
                # Join the drive back in, and stick os.sep in front of the path to
                # make it absolute.
                path = path_drive + os.sep + os.path.join(*path_parts)

                # Check if the drive assumptions above were correct. If path_drive
                # is set, and os.path.splitdrive does not return a drive, it wasn't
                # reall a drive. Put the path together again treating path_drive
                # as a normal path component.
                if path_drive and not os.path.splitdrive(path):
                    path = os.sep + os.path.join(path_drive, *path_parts)

                # Use io.open since we need to add a release_conn method, and
                # methods can't be added to file objects in python 2.
                resp.raw = io.open(path, "rb")
                resp.raw.release_conn = resp.raw.close
        except IOError as e:
            if e.errno == errno.EACCES:
                resp.status_code = codes.forbidden
            elif e.errno == errno.ENOENT:
                resp.status_code = codes.not_found
            else:
                resp.status_code = codes.bad_request

            # Wrap the error message in a file-like object
            # The error message will be localized, try to convert the string
            # representation of the exception into a byte stream
            resp_str = str(e).encode(locale.getpreferredencoding(False))
            resp.raw = BytesIO(resp_str)
            resp.headers['Content-Length'] = len(resp_str)

            # Add release_conn to the BytesIO object
            resp.raw.release_conn = resp.raw.close
        else:
            resp.status_code = codes.ok

            # If it's a regular file, set the Content-Length
            resp_stat = os.fstat(resp.raw.fileno())
            if stat.S_ISREG(resp_stat.st_mode):
                resp.headers['Content-Length'] = resp_stat.st_size

        return resp

    def close(self):
        pass
