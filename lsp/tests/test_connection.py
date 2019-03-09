import json
from datetime import date
from typing import Dict, Tuple

import pytest
from .._role import Role
from .._events import RequestSent, DataSent, MessageEnd
from .._connection import Connection
from .._errors import LspProtocolError
from .._state import IDLE, SEND_BODY


@pytest.fixture
def conn():
    return Connection("client")


def test_connection_initialize():
    conn = Connection("client")
    assert conn.our_role == Role.CLIENT
    assert conn.their_role == Role.SERVER
    assert conn.our_state == IDLE
    assert conn.their_state == IDLE

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
        conn.our_state == SEND_BODY
    ), "while send request header, the state should changed."


def test_send_header_more_than_once(conn: Connection):
    with pytest.raises(LspProtocolError):
        event = RequestSent({"Content-Length": 30})
        conn.send(event)
        # send request header more than once
        conn.send(event)


def test_send_body_before_header_sent(conn: Connection):
    with pytest.raises(LspProtocolError):
        event = DataSent({"data": "testhaha"})
        conn.send(event)


def test_send_too_much_data(conn: Connection):
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
        conn.send(MessageEnd())


def test_send_data():
    conn = Connection("client")
    data = {"method": "didOpen"}
    length = len(json.dumps(data).encode("utf-8"))
    event = RequestSent({"Content-Length": length})
    conn.send(event)
    data_event = DataSent({"data": data})
    data = conn.send(data_event)
    conn.send(MessageEnd())  # remember to send message end event.
    assert data == b'{"method": "didOpen"}'

    # Test for DataSent event with binary data
    conn = Connection("client")
    event = RequestSent({"Content-Length": 30})
    conn.send(event)
    data_event = DataSent({"data": "test_data"})
    data = conn.send(data_event)
    assert data == b"test_data"


def _header_parser(data: bytes) -> Dict[str, str]:
    data_str = data.decode("ascii")
    row_splitter = "\r\n"
    parsed_data = {}
    for row in data_str.split(row_splitter):
        if row:
            key, val = row.split(": ")
            parsed_data[key] = val
    return parsed_data


def test_send_header(conn: Connection):
    event = RequestSent({"Content-Length": 30})
    data = conn.send(event)

    assert _header_parser(data) == {
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
        "Content-Length": "30",
    }


def _binary_parser(data: bytes) -> Tuple[Dict, Dict]:
    def _extract_header():
        header_str = header_bytes.decode("ascii")
        results = {}
        rows = header_str.split("\r\n")
        for row in rows:
            key, val = row.split(": ")
            results[key] = val
        return results

    def _extract_body():
        return json.loads(body_bytes.decode("utf-8"))

    header_bytes, body_bytes = data.split(b"\r\n\r\n")
    header = _extract_header()
    body = _extract_body()
    return header, body


def test_send_json(conn: Connection):
    json_data = {"method": "didOpen"}
    data = conn.send_json(json_data)
    parsed_header, parsed_data = _binary_parser(data)
    assert parsed_header == {
        "Content-Length": "21",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    assert parsed_data == {"method": "didOpen"}


def test_send_json_while_the_state_is_not_idle(conn: Connection):
    conn.send(RequestSent({"Content-Length": 10}))
    with pytest.raises(RuntimeError):
        conn.send_json({"method": "didOpen"})


def test_send_json_with_custom_encoder(conn: Connection):
    class _Encoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, date):
                return f"{o.year}-{o.month}-{o.day}"
            return super(_Encoder, self).default(o)

    json_data = {"method": date(2010, 1, 1)}
    data = conn.send_json(json_data, encoder=_Encoder)
    parsed_header, parsed_data = _binary_parser(data)
    assert parsed_header == {
        "Content-Length": "22",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    assert parsed_data == {"method": "2010-1-1"}


def test_receive_data(conn: Connection):
    conn.receive(b'testdata')
    assert conn.in_buffer.raw == b'testdata'

    conn.receive(b'test')
    assert conn.in_buffer.raw == b'testdatatest'


def test_next_circle(conn: Connection):
    pass


def test_next_circle_when_state_is_invalid(conn: Connection):
    with pytest.raises(LspProtocolError):
        conn.go_next_circle()

    # test when client is sending data
    conn.send(RequestSent({"Content-Length": 300}))
    with pytest.raises(LspProtocolError):
        conn.go_next_circle()

    # test when server is receiving data
    server_conn = Connection("server")
    with pytest.raises(LspProtocolError):
        server_conn.go_next_circle()
