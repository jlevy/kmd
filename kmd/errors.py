"""
Unified hierarchy of error types. These inherit from standard errors like
ValueError and FileExistsError but are more fine-grained.
"""

from typing import Tuple, Type


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


def _nonfatal_exceptions() -> Tuple[Type[Exception], ...]:
    from xonsh.tools import XonshError

    exceptions = [
        SelfExplanatoryError,
        FileNotFoundError,
        IOError,
        XonshError,
    ]

    try:
        import litellm

        exceptions.append(litellm.exceptions.APIError)
    except ImportError:
        pass

    try:
        import yt_dlp

        exceptions.append(yt_dlp.utils.DownloadError)
    except ImportError:
        pass

    return tuple(exceptions)


NONFATAL_EXCEPTIONS = _nonfatal_exceptions()
"""Exceptions that are not fatal and usually don't merit a full stack trace."""
