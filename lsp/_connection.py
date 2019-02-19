from typing import Iterable
from ._events import _EventBase


class Connection:
    """ Language server protocol Connection object. """

    def __init__(self):
        pass

    def send_data(self, data: bytes) -> None:
        """ send data and update the connection state.

        Args:
            data (bytes): data we need to send
        """
        pass

    def receive_data(self, data: bytes) -> Iterable[_EventBase]:
        """ receive data and convert them to a list of event.

        Args:
            data (bytes): data we are received.
        Returns:
            An iterable of lsp event object.
        """
        pass

    def data_to_send(self) -> bytes:
        """ Returns data when we can send to the other side.

        Returns:
            data in bytes.
        """
        pass
