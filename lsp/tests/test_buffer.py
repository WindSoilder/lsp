import pytest
from .._buffer import FixedLengthBuffer


def test_buffer_init_state():
    buffer = FixedLengthBuffer()
    assert buffer.length == 0
    assert buffer.data == b""
    assert buffer.length_set is False


def test_buffer_set_length():
    buffer = FixedLengthBuffer()
    buffer.set_length(30)

    assert buffer.length == 30
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
        buffer.length == 27
    ), "After appending data, the length of buffer should be less"
    assert (
        buffer.data == b"456"
    ), "After appending data, there should have data in buffer"

    buffer.append(b"789")
    assert (
        buffer.length == 24
    ), "After appending data, the length of buffer should be less"
    assert (
        buffer.data == b"456789"
    ), "After appending data, there should have data in buffer"

    buffer.append(b"x" * 24)
    assert buffer.length == 0
    assert buffer.data == b"456" + b"789" + b"x" * 24


def test_buffer_append_too_much_data():
    buffer = FixedLengthBuffer()
    buffer.set_length(2)
    with pytest.raises(RuntimeError):
        buffer.append(b"x" * 3)


def test_clear():
    buffer = FixedLengthBuffer()
    buffer.set_length(2)

    buffer.clear()
    assert buffer.length == 0
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
