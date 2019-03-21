""" Contains events definition which is exposed by lsp.

We can initialize EventClass by this way:
event = RequestSent({'Content-Length': 90})
"""

import warnings
import json
from typing import Set, List, Tuple, Dict, Any, Optional


__all__ = [
    # Mainly used by server
    "RequestReceived",
    "ResponseSent",
    # Mainly userd by client
    "ResponseReceived",
    "RequestSent",
    # Common
    "DataSent",
    "DataReceived",
    "MessageEnd",
    "Close",
    "MessageEnd",
]


# Details:
# 1. MetaClass should derived from type
# 2. When we are creating a class, the MetaClass' __new__, __init__ function
#    will be invoked one by one, just like type(class_name, bases, attributes)
# For more information, please see two useful links:
# https://stackoverflow.com/questions/100003/what-are-metaclasses-in-python
# https://docs.python.org/3/reference/datamodel.html#metaclasses

# NOTE: because it's just the helper implementation of event class definition
# so we needn't test for it.
class _EventBaseMeta(type):  # pragma: no cover
    """ MetaClass for lsp events.

    When a class using this metaclass, the '_required' fields will be
    auto-generated.  And it required class should have '_fields' attribute.
    """

    def __new__(cls, cls_name: str, bases: Tuple, attrs: Dict) -> type:
        if bases is None:
            assert (
                "_fields" in attrs
            ), "The new creating class must contains '_fields' attribute"
        return super(_EventBaseMeta, cls).__new__(cls, cls_name, bases, attrs)

    def __init__(cls, cls_name, bases, attrs):  # type: ignore
        if not hasattr(cls, "_defaults"):
            cls._defaults: List[Tuple[str, str]] = []

        # check if there are too much optional_fields.
        # Any fields which is in _defaults but not in _fields is not allowed.
        optional_fields = set([default_field[0] for default_field in cls._defaults])
        invliad = optional_fields - cls._fields
        if invliad:
            raise ValueError(
                f"Optional contains fields {invliad} which is not existed on _fields"
            )

        cls._required = cls._fields - optional_fields


class EventBase(metaclass=_EventBaseMeta):
    """ Very very base definition for lsp events.

    Attributes:
        _fields (Set[str]): A set of fields in the events.
        _defaults (List[Tuple[str, Any]]): A list of tuple contains
            (field_name, default_value).
        _required (Set[str]): It's worth to know that the _required fields will
            be FILLED AUTOMATICALLY during the class creation.  Subclass can use
            this field WITHOUT worry about creation.  When a fields is not optional
            (which lays in _defaults), it's required.

    Example:
        class SendHeader(EventBase):
            _fields = {"field1", "field2"}
            _defaults = [("field1", "go")]

        After the class creation, the value of SendHeader._required is {"field2"}
    """

    _fields: Set[str] = set()
    _defaults: List[Tuple[str, Any]] = []

    def __init__(self, kwargs: Optional[Dict] = None):  # type: ignore
        if kwargs is None:
            return
        keys = set(kwargs.keys())
        missing_required = self.__class__._required - keys
        # check for fields
        if missing_required:
            raise ValueError(f"Missing required fields: {missing_required}")
        too_much_fields = keys - self._fields
        if too_much_fields:
            warnings.warn(
                f"There are too much fields: {too_much_fields}, I will ignore them."
            )

        self.__dict__.update(self._defaults)
        self.__dict__.update(kwargs)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def to_data(self, encoding: str = "ascii") -> bytes:
        """ convert event into bytes.

        Args:
            encoding (str): the encoding we use to encode data.
        Returns:
            bytes which represent event.
        """
        raise NotImplementedError()


class DataEvent(EventBase):
    """ The DataEvent are fired when we deal with actual data. """

    _fields = {"data"}

    def to_data(self, encoding: str = "utf-8") -> bytes:
        if isinstance(self["data"], (bytes, bytearray)):
            data = bytes(self["data"])
        elif isinstance(self["data"], str):
            data = self["data"].encode(encoding)
        elif isinstance(self["data"], (list, dict)):
            data = json.dumps(self["data"]).encode(encoding)
        return data


class DataReceived(DataEvent):
    """ The DataReceived events are fired when we get request data. """

    _fields = {"data"}


class DataSent(DataEvent):
    """ The DataSent events are fired when we send request/response data. """

    _fields = {"data"}


class _HeaderEvent(EventBase):
    """ Fired when header is sent. """

    _fields = {"Content-Length", "Content-Type"}
    _defaults = [("Content-Type", "application/vscode-jsonrpc; charset=utf-8")]

    def to_data(self, encoding: str = "ascii") -> bytes:
        row_spliter = "\r\n"
        rows = []
        for field in self._fields:
            rows.append(f"{field}: {self[field]}")
        # because the splitter between header part and
        # data part is \r\n, we need to add two \r\n
        rows.append("")
        rows.append("")
        # The header is encoded in ascii, by the definition of lsp
        return row_spliter.join(rows).encode("ascii")


class RequestReceived(_HeaderEvent):
    """ The RequestReceived events are fired when we get request header. """

    pass


class RequestSent(_HeaderEvent):
    """ Fired when request header is sent. """

    pass


class ResponseReceived(_HeaderEvent):
    """ The ResponseReceived events are fired when we get response header. """

    pass


class ResponseSent(_HeaderEvent):
    """ Fired when response header is sent. """

    pass


class Close(EventBase):
    """ Fired when we need to close connection. """

    def to_data(self, encoding: str = "ascii") -> bytes:
        return b""


class MessageEnd(EventBase):
    """ Fired when we send data complete. """

    def to_data(self, encoding: str = "ascii") -> bytes:
        return b""
