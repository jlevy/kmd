from datetime import timezone


def iso_format_z(datetime_obj, microseconds=True) -> str:
    """
    Format a datetime as an ISO 8601 timestamp. Includes the Z for clarity that it is UTC.

    Example with microseconds: 2015-09-12T08:41:12.397217Z
    Example without microseconds: 2015-09-12T08:41:12Z
    """
    timespec = "microseconds" if microseconds else "seconds"
    return datetime_obj.astimezone(timezone.utc).isoformat(timespec=timespec).replace("+00:00", "Z")
