import warnings
import json
from unittest import mock
import pytest

from .._events import (
    EventBase,
    RequestReceived,
    RequestSent,
    ResponseReceived,
    ResponseSent,
    Close,
    MessageEnd,
    DataReceived,
    DataSent,
)


def test_event_subclass_definition():
    # test all fields are optional
    class Event1(EventBase):
        _fields = {"content-length", "content-type"}
        _defaults = [("content-length", 10), ("content-type", "json")]

    assert Event1._required == set()
    assert Event1._fields == {"content-length", "content-type"}
    assert Event1._defaults == [("content-length", 10), ("content-type", "json")]

    # test partial fields are required
    class Event1(EventBase):
        _fields = {"content-length", "content-type"}
        _defaults = [("content-type", "json")]

    assert Event1._required == {"content-length"}


def test_event_subclass_definition_when_defaults_not_given():
    # there are two fields
    class Event1(EventBase):
        _fields = {"content_length", "content_type"}

    assert Event1._defaults == []
    assert Event1._required == {"content_length", "content_type"}
    assert Event1._fields == {"content_length", "content_type"}

    # there are actually no fields
    class Event2(EventBase):
        _fields = set()

    assert Event2._defaults == []
    assert Event2._required == set()
    assert Event2._fields == set()


def test_event_subclass_definition_when_defaults_contains_too_much():
    with pytest.raises(ValueError):

        class Event1(EventBase):
            _fields = {"content_length"}
            _defaults = [("content_length", 10), ("content_length2", 100)]

    with pytest.raises(ValueError):

        class Event2(EventBase):
            _defaults = [("content_length", 10)]


def test_event_object_initialization():
    class Event1(EventBase):
        _fields = {"content-length"}

    event = Event1({"content-length": 10})
    assert getattr(event, "content-length", 10)


def test_event_object_initialization_when_too_many_fields_given():
    class Event1(EventBase):
        _fields = {"content-length", "content-type"}

    with mock.patch.object(warnings, "warn") as stub_warn:
        Event1({"content-length": 10, "content-type": "json", "asset": 1})
        stub_warn.assert_called_once()


def test_event_object_initialization_when_miss_required_fields():
    class Event1(EventBase):
        _fields = {"content-length", "content-type"}
        _defaults = [("content-type", "json")]

    with pytest.raises(ValueError):
        Event1({"content-type": "text"})


def test_event_object_initialization_defaults_fields():
    # test for given _fields override _default fields
    class Event1(EventBase):
        _fields = {"content-length", "content-type"}
        _defaults = [("content-type", "json")]

    event = Event1({"content-length": 10, "content-type": "csv"})
    assert getattr(event, "content-length") == 10
    assert getattr(event, "content-type") == "csv"

    # test for all _default fields
    class Event2(EventBase):
        _fields = {"content-length", "content-type", "using-chunk"}
        _defaults = [
            ("content-length", 10),
            ("content-type", "json"),
            ("using-chunk", False),
        ]

    event = Event2({})
    assert getattr(event, "content-length") == 10
    assert getattr(event, "content-type") == "json"
    assert getattr(event, "using-chunk") is False


def test_access_event_fields():
    class Event1(EventBase):
        _fields = {"content-length", "content-type"}
        _defaults = [("content-length", 10), ("content-type", "json")]

    event = Event1({})
    assert event["content-length"] == 10
    assert event["content-type"] == "json"


@pytest.mark.parametrize(
    "event_cls", [RequestReceived, RequestSent, ResponseReceived, ResponseSent]
)
def test_header_event_to_data(event_cls):
    length = 100
    expect_data = {
        "Content-Length": f"{length}",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    event = event_cls({"Content-Length": length})
    data = event.to_data().decode("ascii")

    parsed_data = {}
    lines = data.split("\r\n")
    assert len(lines) == 4
    assert lines[-1] == ""
    assert lines[-2] == ""
    lines = lines[:-2]
    for line in lines:
        key, val = line.split(": ")
        parsed_data[key] = val
    assert parsed_data == expect_data


@pytest.mark.parametrize("event_cls", [DataReceived, DataSent])
def test_data_event_to_data(event_cls):
    # data event can be initialized by three ways:
    # 1. just from bytes object
    event = event_cls({"data": b"test_data"})
    assert event.to_data() == b"test_data"

    # 2. from string
    event = event_cls({"data": "test_data"})
    assert event.to_data() == b"test_data"

    # 3. from json object
    event = event_cls({"data": {"method": "didOpen"}})
    assert json.loads(event.to_data().decode("utf-8")) == {"method": "didOpen"}

    # 4. from byte_array object
    event = event_cls({"data": bytearray(b"test_data2")})
    assert isinstance(event.to_data(), bytes)
    assert event.to_data() == b"test_data2"


def test_evnet_donent_implement_to_data():
    class Event1(EventBase):
        _fields = {"content-length"}

    event = Event1({"content-length": "30"})
    with pytest.raises(NotImplementedError):
        event.to_data()


# Close event, MessageEnd event are just for signal, which shouldn't contains
# any data.
@pytest.mark.parametrize("event_cls", [Close, MessageEnd])
def test_empty_data(event_cls):
    event = event_cls()
    assert event.to_data() == b""
