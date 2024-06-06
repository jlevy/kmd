class KmdRuntimeError(Exception):
    """
    Base class for kmd errors.
    """

    pass


class ApiResultError(KmdRuntimeError):
    """
    Raised when an API doesn't behave as expected.
    """

    pass


class CommonError(KmdRuntimeError):
    """
    Common errors arise from normal problems. The problem should explain itself
    and no stack trace should be necessary.
    """

    pass


class InvalidInput(CommonError):
    """
    Raised when the wrong kind of input is given to an action or command.
    """

    pass


class InvalidStoreState(CommonError):
    """
    Raised when the store is in an invalid state.
    """

    pass


class ContentError(CommonError):
    """
    Raised when content is invalid.
    """

    pass
