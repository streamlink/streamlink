Validation schemas
==================

.. currentmodule:: streamlink.plugin.api.validate

Introduction
------------

The :ref:`streamlink.plugin.api.validate <api/validate:Validation schemas>` module provides an API for defining declarative
validation schemas which are used to verify and extract data from various inputs, for example HTTP responses.

Validation schemas are a powerful tool for :ref:`plugin <api/plugin:Plugin>` implementors to find and extract data like
stream URLs, stream metadata and more from websites and web APIs.

Instead of verifying and extracting data programatically and having to perform error handling manually,
declarative validation schemas allow defining comprehensive validation and extraction rules which are easy to understand
and which raise errors with meaningful messages upon extraction failure.

.. admonition:: Public interface
   :class: caution

   While the internals are implemented in the ``streamlink.validate`` package,
   :ref:`streamlink.plugin.api.validate <api/validate:Validation schemas>` provides the main public interface
   for plugin implementors.


Examples
--------

Simple schemas
^^^^^^^^^^^^^^

Let's begin with a few simple validation schemas which are not particularly useful yet.

.. code-block:: pycon

    >>> from streamlink.plugin.api import validate

    >>> schema_one = validate.Schema("123")
    >>> schema_two = validate.Schema(123)
    >>> schema_three = validate.Schema(int, 123.0)

    >>> schema_one.validate("123")
    '123'
    >>> schema_two.validate(123)
    123
    >>> schema_three.validate(123)
    123

First, three :class:`Schema` instances are created, ``schema_one``, ``schema_two`` and ``schema_three``.

The :class:`Schema` class is the main schema validation interface and the outer wrapper for all schema definitions.
It is a subclass of :class:`validate.all <all>` which additionally implements the :meth:`Schema.validate()` method.
This interface is expected by various Streamlink methods and functions when passing the ``schema`` argument/keyword,
for example to the :class:`HTTPSession <streamlink.session.Streamlink.http>` methods or :mod:`streamlink.utils.parse` functions.

The :class:`validate.all <all>` class takes a sequence of schema object arguments and validates each one in order.
All schema objects in this schema container must be valid.

Schema objects can be anything, and depending on their type, different validations will be applied. In our example, both
``schema_one`` and ``schema_two`` contain only one schema object, namely ``"123"`` and ``123`` respectively, whereas
``schema_three`` contains two schema objects, ``int`` and ``123.0``. This means that the first two schemas validate
only one condition, while the third one validates two, first ``int``, then ``123.0``.

As you've probably already noticed, validation schemas also have a return value for their extraction purpose, but this isn't
much interesting in this example.

The ``"123"``, ``123`` and ``123.0`` schemas are simple :func:`equality validations <validate>`. This is the case for
all basic objects, and all they do is validate and return the input value again. ``int`` however is a ``type`` object,
and thus a :func:`type validation <_validate_type>`, which checks whether the input is an instance of the schema object
and then also returns the input value again. Since ``123`` is an ``int``, the schema is valid for that input.
``schema_three`` however hasn't finished validating yet at this point, as it defines two validation schemas in total.
This means that the return value of the ``int`` validation gets passed to the ``123.0`` schema validation, and as expected
when checking ``123 == 123.0``, despite both the input and schema being different types, namely ``int`` and ``float``,
the validation succeeds and returns its input value again, causing the return value of the whole
``schema_three`` to be ``123``.

Now let's have a look at validation errors.

.. code-block:: pycon

    >>> schema_one.validate(123)
    streamlink.exceptions.PluginError: Unable to validate result: ValidationError(equality):
      123 does not equal '123'

    >>> schema_three.validate(123.0)
    streamlink.exceptions.PluginError: Unable to validate result: ValidationError(type):
      Type of 123.0 should be int, but is float

The first :meth:`Schema.validate()` call passes ``123`` to ``schema_one``. ``schema_one`` however expects ``"123"``, so
a :class:`ValidationError <streamlink.validate._exception.ValidationError>` is raised because the input value is not equal to
the schema. :meth:`Schema.validate()` catches the error and wraps it in
a :class:`PluginError <streamlink.exceptions.PluginError>` with a specific validation message.

The second validation also fails, but here, it's because of the input type. The first sub-schema explicitly checks for
the type ``int``, and despite the following schema being ``123.0``, which is a ``float`` object that would obviously validate
a ``123.0`` ``float`` input when comparing equality, a :class:`ValidationError <streamlink.validate._exception.ValidationError>`
is raised.

Extracting JSON data
^^^^^^^^^^^^^^^^^^^^

The next example shows how to read an optional integer value from JSON data.

.. code-block:: pycon

    >>> from streamlink.plugin.api import validate

    >>> json_schema = validate.Schema(
    ...     str,
    ...     validate.parse_json(),
    ...     {
    ...         "status": validate.any(None, int),
    ...     },
    ...     validate.get("status"),
    ... )

    >>> json_schema.validate("""{"status":null}""")
    None
    >>> json_schema.validate("""{"status":123}""")
    123

    >>> json_schema.validate("""Not JSON""")
    streamlink.exceptions.PluginError: Unable to validate result: ValidationError:
      Unable to parse JSON: Expecting value: line 1 column 1 (char 0) ('Not JSON')

    >>> json_schema.validate("""{"status":"unknown"}""")
    streamlink.exceptions.PluginError: Unable to validate result: ValidationError(dict):
      Unable to validate value of key 'status'
      Context(AnySchema):
        ValidationError(equality):
          'unknown' does not equal None
        ValidationError(type):
          Type of 'unknown' should be int, but is str

Once again, we start with a new :class:`Schema` object which gets assigned to ``json_schema``. This schema collection validates
four schemas in total. Each of them must be valid, with each output being the input of the next one.

Since our goal is to parse JSON data and extract data from it, this means that we should only accept string inputs, so we set
``str`` as the first schema in this :class:`validate.all <all>` schema collection.

Next is the :func:`validate.parse_json() <parse_json>` validation, a call of a utility function which returns
a :class:`validate.transform <transform>` schema object that does exactly what its name suggests: it takes an input and returns
something else. In this case, obviously, strings are the input and a parsed JSON object is the output, assuming that the input
is indeed valid JSON data.

Now we validate the parsed JSON object. We expect the JSON data to be a JSON ``object``, so we let the next validation schema
be a :func:`dict validation <_validate_dict>`. :class:`dict` validation schemas define a set of key-value pairs which
must exist in the input, unless keys are set as optional using :class:`validate.optional <optional>`.
For the sake of simplicity, this isn't the case in this example just yet. Each value of the key-value pairs is
a validation schema on its own where the input is validated against.

Here, the ``"status"`` key has a :class:`validate.any <any>` validation schema, which is also a schema collection, similar to
:class:`validate.all <all>`, but :class:`validate.any <any>` requires at least one sub-schema to be valid, not all.
Each sub-schema receives the same input, and the output of the overall schema collection is the output of the first sub-schema
that's valid. For our example, this means that the value of the ``status`` key in the JSON data must either be
``None`` (``null``) or an ``int``.

If any of the schemas in a nested schema definition like that fails, then a validation error stack will be generated
by :class:`ValidationError <streamlink.validate._exception.ValidationError>`, as shown above.

The last of the four schemas in the outer :class:`validate.all <all>` schema collection is a :class:`validate.get <get>` schema.
This schema works on any kind of input which implements :func:`__getitem__()`, for example :class:`dict` objects.
And as expected, it attempts to get and return the ``"status"`` key of the output of the previous :class:`dict` validation.
The :mod:`validation <streamlink.plugin.api.validate>` module also supports getting multiple values at once using
the :class:`validate.union <union>` or :class:`validate.union_get <union_get>` schemas, but this isn't relevant here.

Finding stream URLs in HTML
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's imagine a simple website where a stream URL is embedded as JSON data in a ``data-player`` attribute of an unknown
HTML element where the web player of that website reads from.

Extracting this data could be done by using regular expressions, but then we'd have to take HTML syntax into account,
as well as JSON syntax which should usually be HTML-encoded in that HTML element attribute, which would make writing
a regular expression even harder, apart from the fact that the JSON data structure could easily change at any time.

Therefore it would make much more sense parsing the HTML data, querying the resulting node tree using an XPath query
for getting the attribute value, then parsing the JSON data and finally finding and validating the stream URL.

We also don't want to raise validation errors unnecessarily when the user inputs a URL where no video player was found,
so we can instead return an empty list of streams in our plugin implementation and let Streamlink's CLI exit gracefully.
Validation errors are only supposed to be raised when an actual error happened due to unexpected data,
not when streams are offline or inaccessible.

Thanks to validation schemas, we can do all this declaratively without causing a mess when doing this programmatically.

.. code-block:: pycon

    >>> from streamlink.plugin.api import validate

    >>> schema = validate.Schema(
    ...     validate.parse_html(),
    ...     validate.xml_xpath_string(".//*[@data-player][1]/@data-player"),
    ...     validate.none_or_all(
    ...         validate.parse_json(),
    ...         {
    ...             validate.optional("url"): validate.url(
    ...                 path=validate.endswith(".m3u8"),
    ...             ),
    ...         },
    ...         validate.get("url"),
    ...     ),
    ... )

    >>> schema.validate("""
    ...     <!doctype html>
    ...     <section class="no-video-player"></section>
    ... """)
    None

    >>> schema.validate("""
    ...     <!doctype html>
    ...     <section
    ...         class="video-player"
    ...         data-player="{
    ...             &quot;title&quot;:&quot;Offline&quot;
    ...         }"
    ...     >
    ...         ...
    ...     </section>
    ... """)
    None

    >>> schema.validate("""
    ...     <!doctype html>
    ...     <section
    ...         class="video-player"
    ...         data-player="{
    ...             &quot;title&quot;:&quot;Live&quot;,
    ...             &quot;url&quot;:&quot;https://host/hls-playlist.m3u8&quot;
    ...         }"
    ...     >
    ...         ...
    ...     </section>
    ... """)
    'https://host/hls-playlist.m3u8'

    >>> schema.validate("""
    ...     <!doctype html>
    ...     <section
    ...         class="video-player"
    ...         data-player="{
    ...             &quot;title&quot;:&quot;Live&quot;,
    ...             &quot;url&quot;:&quot;https://host/dash-manifest.mpd&quot;
    ...         }"
    ...     >
    ...         ...
    ...     </section>
    ... """)
    streamlink.exceptions.PluginError: Unable to validate result: ValidationError(NoneOrAllSchema):
      ValidationError(dict):
        Unable to validate value of key 'url'
        Context(url):
          Unable to validate URL attribute 'path'
          Context(endswith):
            '/dash-manifest.mpd' does not end with '.m3u8'

We start with a new :class:`Schema` and begin by parsing HTML using the :func:`validate.parse_html() <parse_html>`
utility function. Similar to :func:`validate.parse_json() <parse_json>`, it returns a :class:`validate.transform <transform>`
schema. :func:`validate.parse_html() <parse_html>` however returns a parsed HTML node tree via Streamlink's
:ref:`lxml dependency <install:Dependencies>`.

This is followed by an XPath query schema using the :func:`validate.xml_xpath_string() <xml_xpath_string>` utility function.
:func:`validate.xml_xpath_string() <xml_xpath_string>` is a wrapper for :func:`validate.xml_xpath() <xml_xpath>` which always
returns a string or ``None``, depending on the query result. This is useful for querying text contents or single attribute
values, like in this case. XPath queries on their own always return a result set, i.e. possibly multiple values, so when
trying to find single values, it is important to limit the number of potential return values to only one in the XPath query.

The query here attempts to find any node with a ``data-player`` attribute. It then limits the result set to the first found
element and then reads the value of its ``data-player`` attribute. :func:`validate.xml_xpath_string() <xml_xpath_string>`
turns this into a single string return value, or ``None`` if no or an empty value was returned by the query.

Since we now have two different paths for our overall validation schema, either no player data or still unvalidated player data,
our next schema is a :class:`validate.none_or_all <none_or_all>` schema. This works similar to :class:`validate.all <all>`,
except that ``None`` inputs are skipped and get returned immediately without validating any sub-schemas. This lets us handle
cases where no player was found on the website, without raising
a :class:`ValidationError <streamlink.validate._exception.ValidationError>`.

In the :class:`validate.none_or_all <none_or_all>` schema, we now attempt to parse JSON data, which was already shown
previously, except for the fact that we don't need to validate the ``str`` input here, as the XPath query must have already
returned a string value.

On to the :func:`dict validation <_validate_dict>`. We're only interested in the ``url`` key. Any other keys of the input
will get ignored. Since we're aware that ``url`` can be missing if the stream is offline, we mark it as optional using the
:class:`validate.optional <optional>` schema. This makes the :func:`dict validation <_validate_dict>` not raise an error
if it's missing, but if it's set, then its value must validate. Talking about the value, we want its value to be a URL.

This is where the :func:`validate.url <url>` utility function comes in handy. It parses the input and lets us validate
any parts of the parsed URL with further validation schemas. The return value is always the full URL string. In our example,
we want to ensure that the URL's path ends with the ``".m3u8"`` string, which is an indicator for the stream being
an HLS stream, so we can pass the URL to Streamlink's :class:`HLS implementation <streamlink.stream.HLSStream>`.

Lastly, we simply get the ``url`` key using :class:`validate.get <get>`. The return value must either be ``None`` if no ``url``
key was included in the JSON data, or a ``str`` with a URL where its path ends with ``".m3u8"``.

This means that the overall schema can only return ``None`` or said kind of URL string. If the ``url`` key is not a URL,
or if its path does not end with ``".m3u8"``, then a :class:`ValidationError <streamlink.validate._exception.ValidationError>`
is raised, which is what we want. The ``None`` return value should then be checked accordingly by the plugin implementation.

Validating HTTP responses
^^^^^^^^^^^^^^^^^^^^^^^^^

In order to validate HTTP responses directly, Streamlink's :class:`HTTPSession <streamlink.session.Streamlink.http>` allows
setting the ``schema`` keyword in :meth:`HTTPSession.request() <streamlink.session.Streamlink.http.request>`,
as well as in each HTTP-verb method like ``get()``, ``post()``, etc.

Here's a simple plugin implementation with the same schema from the `Finding stream URLs in HTML`_ example above.

.. code-block:: python
    :caption: example-plugin.py
    :name: example-plugin

    import re

    from streamlink.plugin import Plugin, pluginmatcher
    from streamlink.plugin.api import validate
    from streamlink.stream.hls import HLSStream


    @pluginmatcher(re.compile(r"https://example\.tld/"))
    class ExamplePlugin(Plugin):
        def _get_streams():
            hls_url = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//*[@data-player][1]/@data-player"),
                validate.none_or_all(
                    validate.parse_json(),
                    {
                        validate.optional("url"): validate.url(
                            path=validate.endswith(".m3u8"),
                        ),
                    },
                    validate.get("url"),
                ),
            ))

            if not hls_url:
                return None

            return HLSStream.parse_variant_playlist(self.session, hls_url)


    __plugin__ = ExamplePlugin
