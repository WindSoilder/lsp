import json
from json import JSONEncoder
from typing import Dict, List, Union, Type, Optional

from ._events import (
    EventBase,
    _HeaderEvent,
    DataReceived,
    RequestReceived,
    RequestSent,
    ResponseReceived,
    MessageEnd,
)
from ._state import IDLE, next_state, DONE
from ._role import Role
from ._buffer import ReceiveBuffer
from ._collector import FixedLengthCollector
from ._errors import LspProtocolError


# The implementation of _SentinalCreater is very similar to _StateClassCreater
# But I think we should still split them out, because the sentinal defined here
# is not state.
class SentinalType(type):
    """ Class creater, which is use for define just a semantic const variable. """

    def __str__(self) -> str:
        return self.__name__

    def __repr__(self) -> str:
        return self.__name__


def make_sentinal(name: str) -> SentinalType:
    return SentinalType(name, (), {})


NEED_DATA = make_sentinal("NEED_DATA")


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
        self.in_buffer = ReceiveBuffer()
        self.out_collector = FixedLengthCollector()
        self.in_collector = FixedLengthCollector()

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
            self.out_collector.set_length(event["Content-Length"])
        elif isinstance(event, MessageEnd) and self.out_collector.remain > 0:
            raise LspProtocolError(
                f"Send Message end too quickly. Expect {len(self.out_collector)} bytes."
            )
        else:
            self.out_collector.append(data)
        return data

    def send_json(
        self, data: Union[List[Dict], Dict], encoder: Optional[Type[JSONEncoder]] = None
    ) -> bytes:
        """ helper function for sending data.

        Args:
            data (List or Dict): A valid object which can be dumps to json
            encoder (None or an subclass of json.JSONEncoder): The encoder to encode
                json, if the encoder is None, the default json.JSONEncoder will be used.
        """
        if self.our_state is not IDLE:
            raise RuntimeError("Please ensure that `send` method is never called.")
        self.our_state = DONE
        binary_data = json.dumps(data, cls=encoder).encode("utf-8")
        request_header_event = RequestSent({"Content-Length": len(binary_data)})
        self.out_collector.set_length(len(binary_data))
        self.out_collector.append(binary_data)
        return request_header_event.to_data() + binary_data

    def next_event(self) -> Union[SentinalType, EventBase]:
        """ Parse the next event out of incoming buffer, and return it.

        Note that this method will change the connection according to the status of
        incoming buffer.

        Returns:
            It will return one of the following results:
            1. An event object to indicate that what happened to our incoming buffer.
            2. A special constant NEED_DATA, which indicate that user need to receive
            data from remote server, and calling receive(data).
        """
        if not (self.our_role is Role.CLIENT and self.our_state is DONE):
            raise LspProtocolError("Client can only accept data after it send request.")
        event = self._extract_event()
        if isinstance(event, EventBase):
            # transfer our state
            self.our_state = next_state(self.our_role, self.our_state, event)
        return event

    def receive(self, data: bytes) -> None:
        """ Receive data and feed it to our incoming buffer.  Then we can call
        `next_event` to extrace out incoming events.

        Args:
            data (bytes): the data we received.
        """
        self.in_buffer.append(data)

    def _extract_event(self) -> Union[SentinalType, EventBase]:
        """ parse and extract event from incoming buffer. """
        if self.in_buffer.header_bytes is None:
            header = self.in_buffer.try_extract_header()
            if header is None:
                return NEED_DATA
            else:
                event_obj: _HeaderEvent
                if self.our_role == Role.SERVER:
                    event_obj = RequestReceived(header)
                else:
                    event_obj = ResponseReceived(header)
                self.in_collector.set_length(event_obj["Content-Length"])
                return event_obj
        else:
            data = self.in_buffer.try_extract_data()
            if data is None:
                if self.in_collector.remain == 0:
                    return MessageEnd()
                return NEED_DATA
            else:
                self.in_collector.append(data)
                return DataReceived({"data": data})
