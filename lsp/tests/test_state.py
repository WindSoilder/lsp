import pytest

from .._state import make_state, next_state, IDLE, SEND_BODY, SEND_RESPONSE
from .._role import Role
from .._events import RequestSent, RequestReceived


def test_make_state_and_expect_is_an_instance_of_class():
    test = make_state("test")
    assert isinstance(test, type), "The result of make_state should be type"


def test_make_state_and_we_get_a_proper_name():
    test = make_state("test_state1")
    assert repr(test) == "test_state1"
    assert str(test) == "<State: test_state1>"


def test_next_state():
    # test for client side next_state
    assert SEND_BODY == next_state(Role.CLIENT, IDLE, RequestSent)
    # test for server side next_state
    assert SEND_RESPONSE == next_state(Role.SERVER, IDLE, RequestReceived)


def test_next_state_when_current_state_is_invalid():
    with pytest.raises(RuntimeError):
        next_state(Role.CLIENT, SEND_RESPONSE, RequestSent)


def test_next_state_when_event_is_invalid():
    with pytest.raises(RuntimeError):
        next_state(Role.CLIENT, SEND_BODY, RequestSent)
