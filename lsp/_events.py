""" Contains events definition which is exposed by lsp. """


class EventBase:
    """ Very very base definition for lsp events. """

    pass


class RequestReceived(EventBase):
    """ The RequestReceived events are fired when we get request header. """

    pass


class DataReceived(EventBase):
    """ The DataReceived events are fired when we get request data. """

    pass


class ResponseReceived(EventBase):
    """ The ResponseReceived events are fired when we get response header. """

    pass


class _HeaderSent(EventBase):
    """ INTERNAL EVENT, which is fired when header is sent. """

    pass


class _RequestSent(_HeaderSent):
    """ INTERNAL EVENT, fired when request header is sent. """

    pass


class _ResponseSent(_HeaderSent):
    """ INTERNAL EVENT, fired when response header is sent. """

    pass
