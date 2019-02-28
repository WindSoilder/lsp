class FixedLengthBuffer:
    def __init__(self):  # type: ignore
        self.length: int = 0
        self.data = bytearray()
        self.length_set = False

    def append(self, data: bytes) -> None:
        """ append data into buffer.

        Args:
            data (bytes): data we need to append to.
        Raises:
            RuntimeError - When the length of data is more than the buffer capacity.
        """
        checked_length = self.length - len(data)
        if checked_length < 0:
            raise RuntimeError("Too much data to insert into buffer.")
        self.length -= len(data)
        self.data.extend(data)

    def set_length(self, length: int) -> None:
        """ set the length of buffer.  Note that if the length is set, we can't call
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
        self.length = length
        self.length_set = True

    def clear(self) -> None:
        """ clear the buffer. """
        self.length_set = False
        self.data.clear()
        self.length = 0

    def __len__(self) -> int:
        """ return the length of buffer in bytes. """
        return len(self.data)
