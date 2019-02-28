class LspProtocolError(BaseException):
    """ exception for lsp protocol error.  Mainly contains the following
    errors:
    1. invalid connection state transfer.
    2. send MessageEnd event, but the length of sending buffer doesn't match
    the content of length which defined in the header.
    """

    pass
