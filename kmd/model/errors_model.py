class KmdRuntimeError(ValueError):
    """Base class for kmd runtime errors."""

    pass


class UnexpectedError(KmdRuntimeError):
    """For unexpected errors or runtime check failures."""

    pass


class ApiResultError(KmdRuntimeError):
    """Raised when an API doesn't behave as expected."""

    pass


class WebFetchError(KmdRuntimeError):
    """For web fetching or crawling errors."""

    pass


class SelfExplanatoryError(KmdRuntimeError):
    """Common errors that arise from 'normal' problems that are largely self-explanatory,
    i.e., no stack trace should be necessary when reporting to the user."""

    pass


class InvalidInput(SelfExplanatoryError):
    """Raised when the wrong kind of input is given to an action or command."""

    pass


class InvalidStoreState(SelfExplanatoryError):
    """Raised when the store is not in a valid state for an operation."""

    pass


class SkipperError(SelfExplanatoryError):
    """Errors that are skippable but shouldn't abort the entire operation."""

    pass


class ContentError(SkipperError):
    """Raised when content is not appropriate for an operation."""

    pass


class PreconditionFailure(ContentError):
    """Raised when content is not suitable for the requested operation."""

    pass


class FileFormatError(ContentError):
    """Raised when a file's content format is invalid."""

    pass


class InvalidFilename(ContentError):
    """Raised when a filename is invalid."""

    pass
