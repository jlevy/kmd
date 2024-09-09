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


class FileExists(InvalidInput, FileExistsError):
    """Raised when a file already exists."""

    pass


class FileNotFound(InvalidInput, FileNotFoundError):
    """Raised when a file is not found."""

    pass


class InvalidCommand(InvalidInput):
    """Raised when a command is not valid."""

    pass


class InvalidState(SelfExplanatoryError):
    """Raised when the store or other system state is not in a valid for an operation."""

    pass


class SetupError(SelfExplanatoryError):
    """Raised when a package is not installed or something in the environment
    isn't set up right."""

    pass


class SkippableError(SelfExplanatoryError):
    """Errors that are skippable but shouldn't abort the entire operation."""

    pass


class ContentError(SkippableError):
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
