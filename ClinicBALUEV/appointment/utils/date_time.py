import datetime
from gettext import ngettext

from django.utils import timezone


def combine_date_and_time(date, time) -> datetime.datetime:
    """Combine a date and a time into a datetime object.

    :param date: The date.
    :param time: The time.
    :return: A datetime object.
    """
    return datetime.datetime.combine(date, time)


def get_timestamp() -> str:
    """Get the current timestamp as a string without the decimal part.

    :return: The current timestamp (e.g. "1612345678")
    """
    timestamp = str(timezone.now().timestamp())
    return timestamp.replace(".", "")


def get_weekday_num(weekday: str) -> int:
    """Get the number of the weekday.

    :param weekday: The weekday (e.g. "Monday", "Tuesday", etc.)
    :return: The number of the weekday (0 for Sunday, 1 for Monday, etc.)
    """
    weekdays = {
        "monday": 1,
        "tuesday": 2,
        "wednesday": 3,
        "thursday": 4,
        "friday": 5,
        "saturday": 6,
        "sunday": 0,
    }
    return weekdays.get(weekday.lower(), -1)


def convert_minutes_in_human_readable_format(minutes: float) -> str:
    """Convert a number of minutes in a human-readable format.

    :param minutes: The number of minutes to convert.
    :return: The converted minutes in a human-readable format.
    """
    if minutes == 0:
        return "Не установлено"
    if minutes < 0:
        raise ValueError("Не может быть отрицательным")
    days, remaining_minutes = divmod(int(minutes), 1440)
    hours, minutes = divmod(int(remaining_minutes), 60)

    parts = []
    if hours:
        hours_display = ngettext("%(count)d час", "%(count)d часа", hours) % {
            "count": hours
        }
        parts.append(hours_display)

    if minutes:
        minutes_display = ngettext("%(count)d минут", "%(count)d минут", minutes) % {
            "count": minutes
        }
        parts.append(minutes_display)

    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return "{first_part} and {second_part}".format(
            first_part=parts[0], second_part=parts[1]
        )
    elif len(parts) == 3:
        return "{days}, {hours} and {minutes}".format(
            days=parts[0], hours=parts[1], minutes=parts[2]
        )


def convert_12_hour_time_to_24_hour_time(time_to_convert) -> str:
    # Convert a 12-hour time to a 24-hour time.
    if isinstance(time_to_convert, (datetime.datetime, datetime.time)):
        return time_to_convert.strftime("%H:%M:%S")
    elif isinstance(time_to_convert, str):
        try:
            time_str = time_to_convert.strip().upper()
            return datetime.datetime.strptime(time_str, "%I:%M %p").strftime("%H:%M:%S")
        except ValueError:
            raise ValueError(f"Invalid 12-hour time format: {time_to_convert}")
    else:
        raise ValueError(
            f"Unsupported data type for time conversion: {type(time_to_convert)}"
        )


def convert_str_to_time(time_str: str) -> datetime.time:
    """Convert a string representation of time to a Python `time` object.

    The function tries both 12-hour and 24-hour formats.

    :param time_str: A string representation of time.
    :return: A Python `time` object.
    """
    formats = ["%I:%M %p", "%H:%M:%S", "%H:%M"]

    for fmt in formats:
        try:
            return datetime.datetime.strptime(time_str.strip().upper(), fmt).time()
        except ValueError:
            pass

    raise ValueError(
        f"Invalid time format for '{time_str}'. Expected either a 12-hour (e.g., '10:00 AM') or 24-hour (e.g., "
        f"'13:00:00') format.")


def get_ar_end_time(start_time, duration) -> datetime.time:
    """Get the end time of an appointment request based on the start time and the duration.

    :param start_time: The start time of the appointment request.
    :param duration: The duration in minutes or as timedelta of the appointment request.
    :return: The end time of the appointment request.
    """
    # Check types
    if not isinstance(start_time, (datetime.time, str)):
        raise TypeError("start_time must be a datetime.time object or a string in 'HH:MM:SS' format.")

    if not isinstance(duration, (datetime.timedelta, int, float)):
        raise TypeError("duration must be either a datetime.timedelta or a numeric type representing minutes.")

    if isinstance(duration, (int, float)) and duration < 0:
        raise ValueError("duration cannot be negative.")

    # Convert the time object to a datetime object
    if isinstance(start_time, str):
        start_time = convert_str_to_time(start_time)

    dt_start_time = datetime.datetime.combine(datetime.datetime.today(), start_time)

    # Convert duration to minutes if it's a timedelta
    if isinstance(duration, datetime.timedelta):
        duration_minutes = duration.total_seconds() / 60
    else:
        duration_minutes = int(duration)

    # Add the duration
    dt_end_time = dt_start_time + datetime.timedelta(minutes=duration_minutes)

    # If end time goes past midnight, wrap it around
    if dt_end_time.day > dt_start_time.day:
        dt_end_time = dt_end_time - datetime.timedelta(days=1)

    return dt_end_time.time()
