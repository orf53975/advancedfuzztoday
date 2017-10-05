from json.encoder import JSONEncoder
from _json import encode_basestring as encode_basestring


class MyJSONEncoder(JSONEncoder):
    def __init__(self, injection_mark):
        JSONEncoder.__init__(self)
        self.injection_mark = injection_mark

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        INFINITY = float('inf')

        if self.check_circular:
            markers = {}
        else:
            markers = None

        _encoder = encode_basestring

        def floatstr(o, allow_nan=self.allow_nan,
                     _repr=float.__repr__, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text

        _iterencode = self._make_iterencode(
            markers, self.default, _encoder, self.indent, floatstr,
            self.key_separator, self.item_separator, self.sort_keys,
            self.skipkeys, _one_shot)

        return _iterencode(o, 0)

    def _make_iterencode(self, markers, _default, _encoder, _indent, _floatstr,
                         _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
                         ## HACK: hand-optimized bytecode; turn globals into locals
                         ValueError=ValueError,
                         dict=dict,
                         float=float,
                         id=id,
                         int=int,
                         isinstance=isinstance,
                         list=list,
                         str=str,
                         tuple=tuple,
                         _intstr=int.__str__,
                         ):

        if _indent is not None and not isinstance(_indent, str):
            _indent = ' ' * _indent

        def _iterencode_list(lst, _current_indent_level):
            if not lst:
                yield '[]'
                return
            if markers is not None:
                markerid = id(lst)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = lst
            buf = '['
            if _indent is not None:
                _current_indent_level += 1
                newline_indent = '\n' + _indent * _current_indent_level
                separator = _item_separator + newline_indent
                buf += newline_indent
            else:
                newline_indent = None
                separator = _item_separator
            first = True
            for value in lst:
                if first:
                    first = False
                else:
                    buf = separator
                if isinstance(value, str):
                    # yield buf + _encoder(value)
                    yield buf + _encoder(self.injection_mark.format(value))
                elif value is None:
                    yield buf + self.injection_mark.format('null')
                elif value is True:
                    yield buf + self.injection_mark.format('true')
                elif value is False:
                    yield buf + self.injection_mark.format('false')
                elif isinstance(value, int):
                    # Subclasses of int/float may override __str__, but we still
                    # want to encode them as integers/floats in JSON. One example
                    # within the standard library is IntEnum.
                    yield buf + self.injection_mark.format( _intstr(value))
                elif isinstance(value, float):
                    # see comment above for int
                    yield buf + self.injection_mark.format( _floatstr(value))
                else:
                    yield buf
                    if isinstance(value, (list, tuple)):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                    yield from chunks
            if newline_indent is not None:
                _current_indent_level -= 1
                yield '\n' + _indent * _current_indent_level
            yield ']'
            if markers is not None:
                del markers[markerid]

        def _iterencode_dict(dct, _current_indent_level):
            if not dct:
                yield '{}'
                return
            if markers is not None:
                markerid = id(dct)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = dct
            yield '{'
            if _indent is not None:
                _current_indent_level += 1
                newline_indent = '\n' + _indent * _current_indent_level
                item_separator = _item_separator + newline_indent
                yield newline_indent
            else:
                newline_indent = None
                item_separator = _item_separator
            first = True
            if _sort_keys:
                items = sorted(dct.items(), key=lambda kv: kv[0])
            else:
                items = dct.items()
            for key, value in items:
                if isinstance(key, str):
                    pass
                # JavaScript is weakly typed for these, so it makes sense to
                # also allow them.  Many encoders seem to do something like this.
                elif isinstance(key, float):
                    # see comment for int/float in _make_iterencode
                    key = _floatstr(key)
                elif key is True:
                    key = 'true'
                elif key is False:
                    key = 'false'
                elif key is None:
                    key = 'null'
                elif isinstance(key, int):
                    # see comment for int/float in _make_iterencode
                    key = _intstr(key)
                elif _skipkeys:
                    continue
                else:
                    raise TypeError("key " + repr(key) + " is not a string")
                if first:
                    first = False
                else:
                    yield item_separator
                yield _encoder(key)
                yield _key_separator
                if isinstance(value, str):
                    yield _encoder(self.injection_mark.format( value))
                elif value is None:
                    yield self.injection_mark.format( 'null')
                elif value is True:
                    yield self.injection_mark.format( 'true')
                elif value is False:
                    yield self.injection_mark.format( 'false')
                elif isinstance(value, int):
                    # see comment for int/float in _make_iterencode
                    yield self.injection_mark.format( _intstr(value))
                elif isinstance(value, float):
                    # see comment for int/float in _make_iterencode
                    yield self.injection_mark.format( _floatstr(value))
                else:
                    if isinstance(value, (list, tuple)):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance(value, dict):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                    yield from chunks
            if newline_indent is not None:
                _current_indent_level -= 1
                yield '\n' + _indent * _current_indent_level
            yield '}'
            if markers is not None:
                del markers[markerid]

        def _iterencode(o, _current_indent_level):
            if isinstance(o, str):
                yield _encoder(o)
            elif o is None:
                yield self.injection_mark.format( 'null')
            elif o is True:
                yield self.injection_mark.format( 'true')
            elif o is False:
                yield self.injection_mark.format( 'false')
            elif isinstance(o, int):
                # see comment for int/float in _make_iterencode
                yield self.injection_mark.format( _intstr(o))
            elif isinstance(o, float):
                # see comment for int/float in _make_iterencode
                yield self.injection_mark.format( _floatstr(o))
            elif isinstance(o, (list, tuple)):
                yield from _iterencode_list(o, _current_indent_level)
            elif isinstance(o, dict):
                yield from _iterencode_dict(o, _current_indent_level)
            else:
                if markers is not None:
                    markerid = id(o)
                    if markerid in markers:
                        raise ValueError("Circular reference detected")
                    markers[markerid] = o
                o = _default(o)
                yield from _iterencode(o, _current_indent_level)
                if markers is not None:
                    del markers[markerid]

        return _iterencode