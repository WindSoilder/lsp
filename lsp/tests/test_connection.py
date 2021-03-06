import json
from datetime import date
from typing import Dict, Tuple

import pytest
from .._role import Role
from .._events import (
    RequestSent,
    DataSent,
    ResponseSent,
    DataReceived,
    MessageEnd,
    ResponseReceived,
    RequestReceived,
)
from .._connection import Connection, NEED_DATA
from .._errors import LspProtocolError
from .._state import IDLE, SEND_BODY, SEND_RESPONSE, DONE, CLOSED


@pytest.fixture
def client_conn():
    return Connection("client")


@pytest.fixture
def server_conn():
    return Connection("server")


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


def test_client_send_json(client_conn: Connection):
    json_data = {"method": "didOpen"}
    data = client_conn.send_json(json_data)
    parsed_header, parsed_data = _binary_parser(data)
    assert parsed_header == {
        "Content-Length": "21",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    assert parsed_data == {"method": "didOpen"}


def test_server_send_json(server_conn: Connection):
    # HACK: change the state of server connection
    server_conn.our_state = SEND_RESPONSE
    server_conn.their_state = DONE

    json_data = {"data": "I get it:)"}
    data = server_conn.send_json(json_data)
    parsed_header, parsed_data = _binary_parser(data)

    assert parsed_header == {
        "Content-Length": "22",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    assert parsed_data == {"data": "I get it:)"}

    # then go_next_circle to prepare new data
    server_conn.go_next_circle()
    assert server_conn.our_state == IDLE
    assert server_conn.their_state == IDLE


def test_server_send_json_when_doesn_receive_data_from_client(server_conn: Connection):
    with pytest.raises(LspProtocolError):
        server_conn.send_json({"data": "oh-yeah"})


def test_client_send_json_while_the_state_is_not_idle(client_conn: Connection):
    client_conn.send(RequestSent({"Content-Length": 10}))
    with pytest.raises(LspProtocolError):
        client_conn.send_json({"method": "didOpen"})


def test_send_json_with_custom_encoder(client_conn: Connection):
    class _Encoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, date):
                return f"{o.year}-{o.month}-{o.day}"

    json_data = {"method": date(2010, 1, 1), "arg": 3}
    data = client_conn.send_json(json_data, encoder=_Encoder)
    parsed_header, parsed_data = _binary_parser(data)
    assert parsed_header == {
        "Content-Length": "32",
        "Content-Type": "application/vscode-jsonrpc; charset=utf-8",
    }
    assert parsed_data == {"method": "2010-1-1", "arg": 3}


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
# 2. when client send request, it should change server state.
# 3. when client receive data, the server data should be changed.
# 4. when server receive request, it should change server own state.
# 5. when server receive request, it should change client state.
# 6. when server send data, it should change own state
def test_client_send_change_state(client_conn: Connection):
    # Scenario 1: When client send data, it should change client own state.
    # we should test that after send, our_state is changed.
    event = RequestSent({"Content-Length": 30})
    client_conn.send(event)
    assert (
        client_conn.our_state == SEND_BODY
    ), "while send request header, the state should changed."

    # Scenario 2: When client send request, server state should be changed.
    conn = Connection("client")
    conn.send_json({"method": "didOpen"})
    assert conn.their_state == SEND_RESPONSE

    conn = Connection("client")
    conn.send(RequestSent({"Content-Length": 10}))
    assert conn.their_state == SEND_RESPONSE


def test_client_receive_data_change_server_state(client_conn: Connection):
    # Scenario 3: when client receive data, the server data should be changed.
    client_conn.send_json({"method": "didOpen"})
    next_event = client_conn.next_event()
    assert next_event == NEED_DATA

    client_conn.receive(b"Content-Length: 30\r\n\r\n")
    event = client_conn.next_event()
    assert isinstance(event, ResponseReceived)
    assert client_conn.their_state == SEND_BODY


def test_server_receive_request_change_state(server_conn: Connection):
    # Scenario 4: when server receive request, it should change to
    # SendResponseState
    server_conn.receive(b"Content-Length: 30\r\n\r\n")
    event = server_conn.next_event()
    assert isinstance(event, RequestReceived)
    assert server_conn.our_state == SEND_RESPONSE

    # Scenario 5: when server receive request, the client state should
    # change to SEND_BODY
    assert server_conn.their_state == SEND_BODY


def test_server_next_event_values(server_conn: Connection):
    # 1. server don't receive any data yet.
    event = server_conn.next_event()
    assert event is NEED_DATA
    # 2. server receive header incompletely
    server_conn.receive(b"Content-Length: 30\r\n\r")
    event = server_conn.next_event()
    assert event is NEED_DATA
    # 3. server receive header.
    server_conn.receive(b"\n")
    event = server_conn.next_event()
    assert isinstance(event, RequestReceived)
    # 4. server receive body.
    assert server_conn.next_event() is NEED_DATA
    server_conn.receive(b"x" * 10)
    assert isinstance(server_conn.next_event(), DataReceived)
    assert server_conn.next_event() is NEED_DATA
    # 5. server receive data complete.
    server_conn.receive(b"x" * 20)
    assert isinstance(server_conn.next_event(), DataReceived)
    assert isinstance(server_conn.next_event(), MessageEnd)


def test_server_send_response_change_state(server_conn: Connection):
    # HACK: force go to SEND_RESPONSE state
    server_conn.our_state = SEND_RESPONSE

    server_conn.send(ResponseSent({"Content-Length": 30}))
    assert server_conn.our_state == SEND_BODY
    server_conn.send(DataSent({"data": "x" * 10}))
    assert server_conn.our_state == SEND_BODY
    server_conn.send(DataSent({"data": "x" * 20}))
    # remember to send message end
    server_conn.send(MessageEnd())
    assert server_conn.our_state == DONE


def test_get_received_data(server_conn: Connection):
    server_conn.receive(b"Content-Length: 30\r\n\r\n" + b'"' + b"x" * 28 + b'"')
    server_conn.next_event()
    server_conn.next_event()
    server_conn.next_event()
    # test default arguments
    header, content = server_conn.get_received_data()
    assert header == {"Content-Length": "30"}
    assert content == "x" * 28

    # test raw arguments false arguments
    header, content = server_conn.get_received_data(raw=False)
    assert header == {"Content-Length": "30"}
    assert content == "x" * 28

    # test get received_data with true arguments
    header, content = server_conn.get_received_data(raw=True)
    assert header == {"Content-Length": "30"}
    assert content == b'"' + b"x" * 28 + b'"'


def test_get_received_data_when_we_receive_data_incompletely(server_conn: Connection):
    # receive header in-completely
    server_conn.receive(b"Content-Length: 21\r\n\r")

    with pytest.raises(RuntimeError):
        server_conn.get_received_data()

    # receive header completely, but data in-completely
    server_conn.receive(b"\n" + b'{"method":"2010-1-1"')
    with pytest.raises(RuntimeError):
        server_conn.get_received_data()


def test_close(client_conn: Connection):
    client_conn.close()
    assert client_conn.our_state == CLOSED
    assert client_conn.their_state == CLOSED


def test_send_data_after_closed(client_conn: Connection):
    client_conn.close()

    with pytest.raises(LspProtocolError):
        client_conn.send_json({"method": "didOpen"})


def test_need_data_representation():
    assert str(NEED_DATA) == "NEED_DATA"
    assert repr(NEED_DATA) == "NEED_DATA"


def test_next_event_when_client_doesnt_send_data_yet(client_conn: Connection):
    with pytest.raises(LspProtocolError):
        client_conn.next_event()
