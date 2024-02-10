def format_seconds_to_hr_mm(seconds):
    """Convert seconds to hours and minutes

    Args:
        seconds (int): seconds

    Returns:
        str: hours and minutes
    """
    hours = int(seconds // 3600)
    minutes = int((seconds // 60) % 60)

    if minutes == 0:
        return f"{hours}:00 hrs"
    else:
        return f"{hours}:{minutes} hrs"


def generate_calendar_table(data):
    # Create a dictionary to store the data for each day
    calendar_data = {}
    weekly_duration = {}
    for entry in data:
        week_number = entry["week_number"]
        day_number = entry["day_number"]
        if week_number not in calendar_data:
            calendar_data[week_number] = {}
        calendar_data[week_number][day_number] = entry

    for week, week_data in calendar_data.items():
        total_duration = 0
        for _, day_data in week_data.items():
            total_duration += day_data["duration"]
            day_data["duration_text"] = format_seconds_to_hr_mm(day_data["duration"])
        weekly_duration[week] = format_seconds_to_hr_mm(total_duration)

    return calendar_data, weekly_duration
