from enum import Enum, auto


class Role(Enum):
    """ The enum represent which role I am, I'm a client or server. """

    CLIENT = auto()
    SERVER = auto()
