# Define FixedLengthCollector is helpful because language server protocol
# is fixed-length body protocol.  So the class can help us check out that
# if we add too much data during appending data, which can throw out error
# as soon as possible.


class FixedLengthCollector:
    """ Collector which can handle data, and automatically check out
    if we push too much data into it. """

    def __init__(self):  # type: ignore
        self.remain: int = 0
        self.data = bytearray()
        self.length_set = False

    def append(self, data: bytes) -> None:
        """ append data into collector.

        Args:
            data (bytes): data we need to append to.
        Raises:
            RuntimeError - When the length of data is more than the buffer capacity.
        """
        if self.length_set is False:
            raise RuntimeError(
                "Please call `set_length` to set the length of buffer first."
            )
        checked_length = self.remain - len(data)
        if checked_length < 0:
            raise RuntimeError("Too much data to insert into buffer.")
        self.remain -= len(data)
        self.data.extend(data)

    def set_length(self, length: int) -> None:
        """ set the length of collector.  Note that if the length is set, we can't call
        `set_length` without calling `clear` method.


        Args:
            length (int): the length of buffer
        Raises:
            RuntimeError - When the length is already set
        """
        if self.length_set:
            raise RuntimeError(
                "You have already call set_length.  This can't be called twice"
                "If you wan't to reset length, please call `clear()` first"
            )
        self.remain = length
        self.length_set = True

    def clear(self) -> None:
        """ clear the buffer. """
        self.length_set = False
        self.data.clear()
        self.remain = 0

    def __len__(self) -> int:
        """ return the length of buffer in bytes. """
        return len(self.data)

    def full(self) -> bool:
        """ return True if collect data complete. """
        return self.length_set and self.remain == 0
