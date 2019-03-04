import pytest

from .._state import (
    make_state,
    next_state,
    IDLE,
    SEND_BODY,
    SEND_RESPONSE,
    RECEIVE_DATA,
)
from .._role import Role
from .._events import RequestSent, RequestReceived
from .._errors import LspProtocolError


def test_make_state_and_expect_is_an_instance_of_class():
    test = make_state("test")
    assert isinstance(test, type), "The result of make_state should be type"


def test_make_state_and_we_get_a_proper_name():
    test = make_state("test_state1")
    assert repr(test) == "test_state1"
    assert str(test) == "<State: test_state1>"


def test_next_state():
    # test for client side next_state
    assert SEND_BODY == next_state(
        Role.CLIENT, IDLE, RequestSent({"Content-Length": 10})
    )
    # test for server side next_state
    assert RECEIVE_DATA == next_state(
        Role.SERVER, IDLE, RequestReceived({"Content-Length": 20})
    )


def test_next_state_when_current_state_is_invalid():
    with pytest.raises(LspProtocolError):
        next_state(Role.CLIENT, SEND_RESPONSE, RequestSent({"Content-Length": 10}))


def test_next_state_when_event_is_invalid():
    with pytest.raises(LspProtocolError):
        next_state(Role.CLIENT, SEND_BODY, RequestSent({"Content-Length": 10}))
