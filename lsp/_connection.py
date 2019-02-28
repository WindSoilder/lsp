from ._events import (
    EventBase,
    _HeaderEvent,
    DataReceived,
    DataSent,
    RequestReceived,
    RequestSent,
    ResponseReceived,
    ResponseSent,
    Close,
    MessageEnd,
)
from ._state import IDLE, next_state
from ._role import Role
from ._buffer import FixedLengthBuffer
from ._errors import LspProtocolError


class Connection:
    """ Language server protocol Connection object. """

    def __init__(self, role: str):  # type: ignore
        if role == "client":
            self.our_role = Role.CLIENT
            self.their_role = Role.SERVER
        elif role == "server":
            self.our_role = Role.SERVER
            self.their_role = Role.CLIENT
        else:
            raise ValueError("The `role` value should be one of ('client', 'server')")
        self.our_state = IDLE
        self.their_state = IDLE
        self.in_buffer = FixedLengthBuffer()
        self.out_buffer = FixedLengthBuffer()

    def send(self, event: EventBase) -> bytes:
        """ send event and returns the relative bytes.  So what this function
        do is convert from event object to actual bytes, then user don't need
        to worry about bytes send to server.

        Args:
            event (EventBase): event we need to send.
        Returns:
            Bytes we can send to user.
        """
        # transfer our state
        self.our_state = next_state(self.our_role, self.our_state, event)
        try:
            data = self._handle_event(event)
        except RuntimeError as e:
            raise LspProtocolError from e
        return data

    def _handle_event(self, event: EventBase) -> bytes:
        # convert event into bytes
        data = event.to_data()
        if isinstance(event, _HeaderEvent):
            self.out_buffer.set_length(event["Content-Length"])
        elif isinstance(event, MessageEnd) and self.out_buffer.remain > 0:
            raise LspProtocolError(
                f"Send Message end too quickly.  Expect {len(self.out_buffer)} bytes."
            )
        else:
            self.out_buffer.append(data)
        return data
