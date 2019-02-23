from ._events import EventBase


class Connection:
    """ Language server protocol Connection object. """

    def __init__(self):  # type: ignore
        pass

    def send(self, event: EventBase) -> bytes:
        """ send event and returns the relative bytes.  So what this function
        do is convert from event object to actual bytes, then user don't need
        to worry about bytes send to server.

        Args:
            event (EventBase): event we need to send.
        Returns:
            Bytes we can send to user.
        """
        pass

    def next_event(self) -> EventBase:
        """ get and return next events.  User can do something according
        to what it get.

        Returns:
            An EventBase object
        """
        pass
