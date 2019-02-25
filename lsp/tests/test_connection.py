import json

import pytest
from .._role import Role
from .._events import (
    RequestSent,
    ResponseSent,
    RequestReceived,
    ResponseReceived,
    DataSent,
    MessageEnd,
)
from .._connection import Connection
from .._errors import LspProtocolError
from .._state import IDLE


@pytest.fixture
def conn():
    return Connection("client")


def test_connection_initialize():
    conn = Connection("client")
    assert conn.our_role == Role.CLIENT
    assert conn.their_role == Role.SERVER
    assert conn.our_state == IDLE
    assert conn.thier_state == IDLE

    conn = Connection("server")
    assert conn.our_role == Role.SERVER
    assert conn.their_role == Role.CLIENT

    # make connection with other role is invalid
    with pytest.raises(ValueError):
        Connection("test")


def test_send_change_state(conn: Connection):
    # we should test that after send, our_state is changed.
    event = RequestSent({"Content-Length": 30})
    conn.send(event)
    assert (
        conn.our_state == DataSent
    ), "while send request header, the state should changed."


def test_send_header(conn: Connection):
    event = RequestSent({"Content-Length": 30})
    data = conn.send(event)
    assert (
        data == b'Content-Type: "application/vscode-jsonrpc; charset=utf-8"\r\n'
        b"Content-Length: 30\r\n"
        b"\r\n"
    )
    event = RequestReceived({"Content-Length": 20})
    data = conn.send(event)
    assert (
        data == b'Content-Type: "application/vscode-jsonrpc; charset=utf-8"\r\n'
        b"Content-Length: 20\r\n"
        b"\r\n"
    )
    event = ResponseSent({"Content-Length": 100})
    data = conn.send(event)
    assert (
        data == b'Content-Type: "application/vscode-jsonrpc; charset=utf-8"\r\n'
        b"Content-Length: 20\r\n"
        b"\r\n"
    )
    event = ResponseReceived({"Content-Length": 300})
    data = conn.send(event)
    assert (
        data == b'Content-Type: "application/vscode-jsonrpc; charset=utf-8"\r\n'
        b"Content-Length: 300\r\n"
        b"\r\n"
    )


def test_send_header_more_than_once(conn: Connection):
    with pytest.raises(LspProtocolError):
        event = RequestSent({"Content-Length": 30})
        conn.send(event)
        # send request header more than once
        conn.send(event)


def test_send_body_before_header_sent():
    with pytest.raises(LspProtocolError):
        event = DataSent({"data": "testhaha"})
        conn.send(event)


def test_send_too_much_data():
    with pytest.raises(LspProtocolError):
        event = RequestSent({"Content-Length": 30})
        conn.send(event)
        data_event = DataSent({"data": "a" * 31})
        conn.send(data_event)


def test_end_of_message_too_earily(conn: Connection):
    with pytest.raises(LspProtocolError):
        event = RequestSent({"Content-Length": 30})
        conn.send(event)
        data_event = DataSent({"data": "a" * 29})
        conn.send(data_event)
        # what? you tell me you have no more data? but
        # I just receive 29 characters!  I will throw error!
        conn.send(MessageEnd)


def test_send_data():
    conn = Connection()
    data = {"method": "didOpen"}
    length = len(json.dumps(data).encode("utf-8"))
    event = RequestSent({"Content-Length": length})
    conn.send(event)
    data_event = DataSent({"data": data})
    data = conn.send(data_event)
    conn.send(MessageEnd)  # remember to send message end event.
    assert data == b'{"method": "didOpen"}'

    # Test for DataSent event with binary data
    conn = Connection()
    event = RequestSent({"Content-Length": 30})
    conn.send(event)
    data_event = DataSent({"data": "test_data"})
    data = conn.send(data_event)
    assert data == b"test_data"
