from .._state import make_state


def test_make_state_and_expect_is_an_instance_of_class():
    test = make_state("test")
    assert isinstance(test, type), "The result of make_state should be type"


def test_make_state_and_we_get_a_proper_name():
    test = make_state("test_state1")
    assert repr(test) == "test_state1"
    assert str(test) == "<State: test_state1>"
