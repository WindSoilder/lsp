""" Core implementation for lsp """

import json
from json import JSONEncoder
from typing import Dict, List, Union, Type, Optional, Tuple

from ._events import (
    Close,
    EventBase,
    _HeaderEvent,
    DataReceived,
    DataSent,
    RequestReceived,
    RequestSent,
    ResponseReceived,
    MessageEnd,
    ResponseSent,
)
from ._state import IDLE, next_state, DONE, SEND_RESPONSE
from ._role import Role
from ._buffer import ReceiveBuffer
from ._collector import FixedLengthCollector
from ._errors import LspProtocolError

__all__ = ["Connection", "NEED_DATA"]


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
    """ Language server protocol Connection object.

    Args:
        role (str): represent our role.  Which can be 'cliet' or 'server'
    """

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
            Bytes we can send to other side.
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
            if isinstance(event, RequestSent):
                # client fire RequestSent event, server should goto next_state according
                # to RequestReceived event
                self.their_state = next_state(
                    self.their_role, self.their_state, RequestReceived
                )
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
        Returns:
            Bytes that we can send to other side.
        """

        def _check_state() -> None:
            if self.our_role == Role.SERVER:
                if self.our_state is not SEND_RESPONSE or self.their_state is not DONE:
                    raise LspProtocolError(
                        "Can only send data when we receive request.\n"
                        f"But for now our_state: {self.our_state}, "
                        f"their_state: {self.their_state}"
                    )
            else:
                if self.our_state is not IDLE or self.their_state is not IDLE:
                    raise LspProtocolError(
                        "Our state or their state is not idle, may be you have send "
                        "data but havn't called `go_next_circle` to refresh state?"
                    )

        def _set_state() -> None:
            self.our_state = DONE
            if self.our_role == Role.CLIENT:
                self.their_state = SEND_RESPONSE

        # do state checking.
        _check_state()
        binary_data = json.dumps(data, cls=encoder).encode("utf-8")
        header_event = _HeaderEvent({"Content-Length": len(binary_data)})
        _set_state()
        return header_event.to_data() + binary_data

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
        if self.our_role is Role.CLIENT and self.our_state is not DONE:
            raise LspProtocolError("Client can only accept data after it send request.")
        event = self._extract_event()
        if isinstance(event, EventBase):
            their_event: Union[type, EventBase]
            # when we get RequestReceived/ResponseReceived/DataReceived event, we
            # should change other side's state by RequestSent/ResponseSent/DataSent
            # event.
            if isinstance(event, _HeaderEvent):
                if isinstance(event, RequestReceived):
                    # when server get RequestReceived event, it should change
                    # the state according to this event.
                    self.our_state = next_state(self.our_role, self.our_state, event)
                    their_event = RequestSent
                elif isinstance(event, ResponseReceived):
                    their_event = ResponseSent
            elif isinstance(event, DataReceived):
                their_event = DataSent
            else:
                their_event = event.__class__
            # transfer their_state
            self.their_state = next_state(
                self.their_role, self.their_state, their_event
            )
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
        # we don't get any header yet.
        if self.in_buffer.header_bytes is None:
            header = self.in_buffer.try_extract_header()
            if header is None:  # header data doesn't completely received.
                return NEED_DATA
            else:
                event_obj: _HeaderEvent
                if self.our_role == Role.SERVER:
                    event_obj = RequestReceived(header)
                else:
                    event_obj = ResponseReceived(header)
                self.in_collector.set_length(int(event_obj["Content-Length"]))
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

    def go_next_circle(self) -> None:
        """ go to next request/response circle.

        Raises:
            LspProtocolError - When our state and their state is not done yet.
        """
        # As server: when we receive Notification complete
        # As client: when we cend Notification complete
        # We can just go_next_circle.  But just ensure that client's state is DONE
        # server's state is SEND_RESPONSE
        if self.our_role is Role.CLIENT:
            if self.our_state is not DONE or (
                self.their_state not in (SEND_RESPONSE, DONE)
            ):
                raise LspProtocolError(
                    "As client, my state is not done or server's state is invalid"
                )
        else:
            if (
                self.our_state not in (SEND_RESPONSE, DONE)
                or self.their_state is not DONE
            ):
                raise LspProtocolError(
                    "As client, my state is not SEND_RESPONSE or DONE, "
                    "or client's state is invalid"
                )
        self.our_state = IDLE
        self.their_state = IDLE
        self.in_buffer.clear()
        self.out_collector.clear()
        self.in_collector.clear()

    def get_received_data(
        self, raw: bool = False
    ) -> Tuple[Dict, Union[bytes, Dict, List]]:
        """ A helper method to extract our received data.  This method is useful
        when we get `MessageEnd` event(which indicate we have received data completely).
        And it returns a eaiily-handled python objects.

        Args:
            raw (bool): Indicate that if we should return raw data(in bytes).  Or
                deserialized data.

        Returns:
            A tuple contains (header, data), header has type dict.
            And data's type can be bytes when raw is True(So it can be serialize by
            other json library on user code).  Or it can be a dict or list object.

        Raises:
            Raise RuntimeError when we don't receive data completely.
        """
        header = self.in_buffer.try_extract_header()
        if header is None or not self.in_collector.full():
            raise RuntimeError(
                "Receive data incompletely.  Please call `next_event()` until"
                "Received MessageEnd event"
            )
        if raw is False:
            return header, json.loads(self.in_buffer.raw)
        else:
            return header, bytes(self.in_buffer.raw)

    def close(self) -> None:
        """ Close the connection, make both states go to closed. """
        self.our_state = next_state(self.our_role, self.our_state, Close)
        self.their_state = next_state(self.their_role, self.their_state, Close)
