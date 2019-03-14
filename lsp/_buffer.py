from typing import Optional, Dict


class ReceiveBuffer:
    """ Inner data buffer.  It can receive data, and extract our header part and body
    part later. """

    def __init__(self):  # type: ignore
        self.raw = bytearray()
        self.header_bytes: Optional[bytearray] = None
        self.body_pointer: int = 0

    def append(self, data: bytes) -> None:
        """ Append data into buffer.

        Args:
            data (bytes): the data we need to append.
        """
        self.raw.extend(data)

    def try_extract_header(self) -> Optional[Dict[str, str]]:
        """ Try to extract the header part in the buffer.

        Returns:
            When the buffer received completely header data, then return
            A dict.  Else we return None.
        """

        def _extract_header() -> Dict[str, str]:
            header_str = self.header_bytes.decode("ascii")  # type: ignore
            results = {}
            rows = header_str.split("\r\n")
            for row in rows:
                key, val = row.split(": ")
                results[key] = val
            return results

        data_splitted = self.raw.split(b"\r\n\r\n")
        if len(data_splitted) == 1:  # so we don't receive header data complete yet.
            return None
        else:
            # we have receive header completely, so we can extract header, and if there
            # are any data inputed, we save it to the raw, which indicate that it's
            # un-handled.
            self.header_bytes, self.raw = (
                bytearray(data_splitted[0]),
                bytearray(data_splitted[1]),
            )
            headers = _extract_header()
            return headers

    def try_extract_data(self) -> Optional[bytes]:
        """ Try to extract the actual data in buffer.  Note that we should call
        `try_extract_header` first to extract header out.

        Returns:
            When there are data in the buffer, return it.  Return None to indicate
            there are no data in the buffer.

        Raises:
            RuntimeError - When the buffer doesn't completely handle header data.
        """
        if self.header_bytes is None:
            raise RuntimeError(
                "Header is un-handled yet, please call `try_extract_header` first."
            )
        # TODO: need to rewrite the implementation.  Because the slice operation will
        # copy memeory, and it may be high cost.
        if self.body_pointer == len(self.raw):
            return None
        # fmt: off
        data = self.raw[self.body_pointer:]
        # fmt: on
        self.body_pointer += len(data)
        return data
