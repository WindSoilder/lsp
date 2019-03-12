import pytest
from .._buffer import ReceiveBuffer


def test_receive_buffer_append():
    buffer = ReceiveBuffer()
    buffer.append(b"asdf")
    assert buffer.raw == b"asdf"

    buffer.append(b"ghjk")
    assert buffer.raw == b"asdfghjk"


def test_receive_buffer_try_extract_header():
    buffer = ReceiveBuffer()
    buffer.append(b"Content-Length: 123\r\n\r\n")
    header = buffer.try_extract_header()
    assert header == {"Content-Length": "123"}

    # for now the header is incomplete
    buffer = ReceiveBuffer()
    buffer.append(b"Content-Length: 123\r\n\r")
    header = buffer.try_extract_header()
    assert header is None
    # then we complete the header data
    buffer.append(b"\n")
    header = buffer.try_extract_header()
    assert header == {"Content-Length": "123"}


def test_receive_buffer_try_extract_data():
    buffer = ReceiveBuffer()
    buffer.append(b"Content-Length: 123\r\n\r\n")
    buffer.try_extract_header()

    buffer.append(b"first data")
    data = buffer.try_extract_data()
    assert data == b"first data"
    # when extract data out, we should extract out emtpy data.
    data = buffer.try_extract_data()
    assert data is None
    buffer.append(b"second data")
    data = buffer.try_extract_data()
    assert data == b"second data"


def test_receive_buffer_try_extract_data_when_header_is_unhandled_yet():
    buffer = ReceiveBuffer()
    buffer.append(b"Content-Length:123\r\n\r\n")
    with pytest.raises(RuntimeError):
        buffer.try_extract_data()


def test_receive_buffer_try_extract_data_when_no_data_yet():
    buffer = ReceiveBuffer()
    buffer.append(b"Content-Length: 123\r\n\r\n")
    buffer.try_extract_header()
    data = buffer.try_extract_data()
    assert data is None
