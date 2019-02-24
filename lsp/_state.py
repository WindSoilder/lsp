from typing import Type, Dict
from ._role import Role
from ._events import (
    RequestSent,
    DataSent,
    MessageEnd,
    Close,
    RequestReceived,
    ResponseSent,
    EventBase,
)

__all__ = [
    "make_state",
    "next_state",
    "IDLE",
    "SEND_BODY",
    "DONE",
    "CLOSED",
    "SEND_RESPONSE",
]


class _StateClassCreater(type):
    """ Creater for state class. """

    def __str__(self) -> str:
        return f"<State: {self.__name__}>"

    def __repr__(self) -> str:
        return self.__name__


def make_state(state_name: str) -> Type:
    """ make state as a class.

    Args:
        state_name (str): the state name.
    Returns:
        A state relative class
    """
    return _StateClassCreater(state_name, (), {})


def next_state(role: Role, current_state: Type, event: EventBase) -> Type:
    """ given the role with current state, find the next state when received
    the given event.

    Args:
        role (_role.Role): The role of connection.
        current_state (type): the current state of connection.
        event (EventBase): The event we received.
    Returns:
        An instance of type indicate the next state.
    Raises:
        ValueError - if the current_state is not a valid state of role.
            Or we can't find next state
    """
    state_machine = _client_state if role == Role.CLIENT else _server_state
    if current_state not in state_machine:
        raise ValueError(f"The given state {repr(current_state)} is invalid.")
    next_state = state_machine[current_state].get(event, None)
    if not next_state:
        raise ValueError(f"The event is invalid.")
    return next_state


# States definition
IDLE = make_state("IDLE")
SEND_BODY = make_state("SEND_BODY")
DONE = make_state("DONE")
CLOSED = make_state("CLOSED")
SEND_RESPONSE = make_state("SEND_RESPONSE")


# state machine definieion
_client_state: Dict[type, Dict] = {
    IDLE: {RequestSent: SEND_BODY, Close: CLOSED},
    SEND_BODY: {DataSent: SEND_BODY, Close: CLOSED, MessageEnd: DONE},
    DONE: {Close: CLOSED},
    CLOSED: {},
}

_server_state: Dict[type, Dict] = {
    IDLE: {RequestReceived: SEND_RESPONSE, Close: CLOSED},
    SEND_RESPONSE: {ResponseSent: SEND_BODY, Close: CLOSED},
    SEND_BODY: {DataSent: SEND_BODY, Close: CLOSED, MessageEnd: DONE},
    DONE: {Close: CLOSED},
    CLOSED: {},
}
