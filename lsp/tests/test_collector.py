import pytest
from .._collector import FixedLengthCollector


def test_collector_init_state():
    collector = FixedLengthCollector()
    assert collector.remain == 0
    assert collector.data == b""
    assert collector.length_set is False


def test_collector_set_length():
    collector = FixedLengthCollector()
    collector.set_length(30)

    assert collector.remain == 30
    assert collector.length_set is True


def test_collector_set_length_twice_should_raise_error():
    collector = FixedLengthCollector()
    collector.set_length(30)

    with pytest.raises(RuntimeError):
        collector.set_length(30)


def test_collector_append():
    collector = FixedLengthCollector()
    collector.set_length(30)
    collector.append(b"456")

    assert (
        collector.remain == 27
    ), "After appending data, the length of collector should be less"
    assert (
        collector.data == b"456"
    ), "After appending data, there should have data in collector"

    collector.append(b"789")
    assert (
        collector.remain == 24
    ), "After appending data, the length of collector should be less"
    assert (
        collector.data == b"456789"
    ), "After appending data, there should have data in collector"

    collector.append(b"x" * 24)
    assert collector.remain == 0
    assert collector.data == b"456" + b"789" + b"x" * 24


def test_collector_append_too_much_data():
    collector = FixedLengthCollector()
    collector.set_length(2)
    with pytest.raises(RuntimeError):
        collector.append(b"x" * 3)


def test_collector_append_without_set_length():
    collector = FixedLengthCollector()
    with pytest.raises(RuntimeError):
        collector.append(b"")


def test_clear():
    collector = FixedLengthCollector()
    collector.set_length(2)

    collector.clear()
    assert collector.remain == 0
    assert collector.data == b""
    assert collector.length_set is False

    # test we can call clear many twice without throw any error.
    collector.clear()


def test_collector_length_support():
    collector = FixedLengthCollector()
    collector.set_length(100)

    assert len(collector) == 0
    collector.append(b"test")
    assert len(collector) == 4
