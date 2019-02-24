import warnings
from unittest import mock
import pytest

from .._events import EventBase


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
