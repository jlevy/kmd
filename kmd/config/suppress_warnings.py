import warnings


def filter_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*deprecated.*")
    warnings.filterwarnings("ignore", message=".*Deprecation.*")
    warnings.filterwarnings("ignore", module="pydub")


filter_warnings()
