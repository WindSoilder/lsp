import pytest
from .._buffer import FixedLengthBuffer, ReceiveBuffer


def test_buffer_init_state():
    buffer = FixedLengthBuffer()
    assert buffer.remain == 0
    assert buffer.data == b""
    assert buffer.length_set is False


def test_buffer_set_length():
    buffer = FixedLengthBuffer()
    buffer.set_length(30)

    assert buffer.remain == 30
    assert buffer.length_set is True


def test_buffer_set_length_twice_should_raise_error():
    buffer = FixedLengthBuffer()
    buffer.set_length(30)

    with pytest.raises(RuntimeError):
        buffer.set_length(30)


def test_buffer_append():
    buffer = FixedLengthBuffer()
    buffer.set_length(30)
    buffer.append(b"456")

    assert (
        buffer.remain == 27
    ), "After appending data, the length of buffer should be less"
    assert (
        buffer.data == b"456"
    ), "After appending data, there should have data in buffer"

    buffer.append(b"789")
    assert (
        buffer.remain == 24
    ), "After appending data, the length of buffer should be less"
    assert (
        buffer.data == b"456789"
    ), "After appending data, there should have data in buffer"

    buffer.append(b"x" * 24)
    assert buffer.remain == 0
    assert buffer.data == b"456" + b"789" + b"x" * 24


def test_buffer_append_too_much_data():
    buffer = FixedLengthBuffer()
    buffer.set_length(2)
    with pytest.raises(RuntimeError):
        buffer.append(b"x" * 3)


def test_buffer_append_without_set_length():
    buffer = FixedLengthBuffer()
    with pytest.raises(RuntimeError):
        buffer.append(b"")


def test_clear():
    buffer = FixedLengthBuffer()
    buffer.set_length(2)

    buffer.clear()
    assert buffer.remain == 0
    assert buffer.data == b""
    assert buffer.length_set is False

    # test we can call clear many twice without throw any error.
    buffer.clear()


def test_buffer_length_support():
    buffer = FixedLengthBuffer()
    buffer.set_length(100)

    assert len(buffer) == 0
    buffer.append(b"test")
    assert len(buffer) == 4


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
    assert data == b""
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
    assert data == b""
