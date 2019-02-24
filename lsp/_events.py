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


class DataSent(EventBase):
    """ The DataSent events are fired when we send request/response data. """

    pass


class ResponseReceived(EventBase):
    """ The ResponseReceived events are fired when we get response header. """

    pass


class _HeaderSent(EventBase):
    """ Fired when header is sent. """

    pass


class RequestSent(_HeaderSent):
    """ Fired when request header is sent. """

    pass


class ResponseSent(_HeaderSent):
    """ Fired when response header is sent. """

    pass


class Close(EventBase):
    """ Fired when we need to close connection. """

    pass


class MessageEnd(EventBase):
    """ Fired when we send data complete. """

    pass
