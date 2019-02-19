""" Contains events definition which is exposed by lsp. """


class _EventBase:
    """ Very very base definition for lsp events. """

    pass


class RequestReceived(_EventBase):
    """ The RequestReceived events are fired when we get request header. """

    pass


class DataReceived(_EventBase):
    """ The DataReceived events are fired when we get request data. """

    pass


class ResponseReceived(_EventBase):
    """ The ResponseReceived events are fired when we get response header. """

    pass


class _HeaderSent(_EventBase):
    """ INTERNAL EVENT, which is fired when header is sent. """

    pass


class _RequestSent(_HeaderSent):
    """ INTERNAL EVENT, fired when request header is sent. """

    pass


class _ResponseSent(_HeaderSent):
    """ INTERNAL EVENT, fired when response header is sent. """

    pass
