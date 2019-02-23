from typing import Type


class _StateClassCreater(type):
    """ Creater for state class. """

    def __str__(self) -> str:
        return f"<State: {self.__name__}>"

    def __repr__(self) -> str:
        return self.__name__


def make_state(state_name: str) -> Type:
    """ make state as a class.

    Args:
        state_name: the state name.
    Returns:
        A state relative class
    """
    return _StateClassCreater(state_name, (), {})


# States definition
IDLE = make_state("IDLE")
SEND_BODY = make_state("SEND_BODY")
DONE = make_state("DONE")
CLOSED = make_state("CLOSED")
SEND_RESPONSE = make_state("SEND_RESPONSE")
