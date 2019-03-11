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
def client_conn():
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


def test_send_change_state(client_conn: Connection):
    # we should test that after send, our_state is changed.
    event = RequestSent({"Content-Length": 30})
    client_conn.send(event)
    assert (
        client_conn.our_state == SEND_BODY
    ), "while send request header, the state should changed."


def test_send_header_more_than_once(client_conn: Connection):
    with pytest.raises(LspProtocolError):
        event = RequestSent({"Content-Length": 30})
        client_conn.send(event)
        # send request header more than once
        client_conn.send(event)


def test_send_body_before_header_sent(client_conn: Connection):
    with pytest.raises(LspProtocolError):
        event = DataSent({"data": "testhaha"})
        client_conn.send(event)


def test_send_too_much_data(client_conn: Connection):
    with pytest.raises(LspProtocolError):
        event = RequestSent({"Content-Length": 30})
        client_conn.send(event)
        data_event = DataSent({"data": "a" * 31})
        client_conn.send(data_event)


def test_end_of_message_too_earily(client_conn: Connection):
    with pytest.raises(LspProtocolError):
        event = RequestSent({"Content-Length": 30})
        client_conn.send(event)
        data_event = DataSent({"data": "a" * 29})
        client_conn.send(data_event)
        # what? you tell me you have no more data? but
        # I just receive 29 characters!  I will throw error!
        client_conn.send(MessageEnd())


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


def test_send_header(client_conn: Connection):
    event = RequestSent({"Content-Length": 30})
    data = client_conn.send(event)

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


def test_send_json(client_conn: Connection):
    json_data = {"method": "didOpen"}
    data = client_conn.send_json(json_data)
    parsed_header, parsed_data = _binary_parser(data)
    assert parsed_header == {
        "Content-Length": "21",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    assert parsed_data == {"method": "didOpen"}


def test_send_json_while_the_state_is_not_idle(client_conn: Connection):
    client_conn.send(RequestSent({"Content-Length": 10}))
    with pytest.raises(RuntimeError):
        client_conn.send_json({"method": "didOpen"})


def test_send_json_with_custom_encoder(client_conn: Connection):
    class _Encoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, date):
                return f"{o.year}-{o.month}-{o.day}"
            return super(_Encoder, self).default(o)

    json_data = {"method": date(2010, 1, 1)}
    data = client_conn.send_json(json_data, encoder=_Encoder)
    parsed_header, parsed_data = _binary_parser(data)
    assert parsed_header == {
        "Content-Length": "22",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    assert parsed_data == {"method": "2010-1-1"}


def test_receive_data(client_conn: Connection):
    client_conn.receive(b"testdata")
    assert client_conn.in_buffer.raw == b"testdata"

    client_conn.receive(b"test")
    assert client_conn.in_buffer.raw == b"testdatatest"


def test_next_circle_when_state_is_invalid(client_conn: Connection):
    with pytest.raises(LspProtocolError):
        client_conn.go_next_circle()

    # test when client is sending data
    client_conn.send(RequestSent({"Content-Length": 300}))
    with pytest.raises(LspProtocolError):
        client_conn.go_next_circle()

    # test when server is receiving data
    server_conn = Connection("server")
    with pytest.raises(LspProtocolError):
        server_conn.go_next_circle()


#############################################
# test for state changing.                  #
#############################################
# Some important scenarios
# 1. when client send data, it should change client own state.
# 2. when client receive data, the server data should be changed.
# 3. when server receive data, it should change server own state.
# 4. when server send data, it should change own state
