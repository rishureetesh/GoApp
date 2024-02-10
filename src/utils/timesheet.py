import pandas as pd

from datetime import datetime, timedelta

from src.utils.date_time import generate_calendar_table, format_seconds_to_hr_mm
from src.utils.pdf_generation import generate_timesheet_pdf


def generate_timesheet_calendar(time_charges, details, work_order):
    df = pd.DataFrame(list(map(lambda x: x.dict(), time_charges)))
    df = df[["id", "description", "startTime", "endTime", "invoiced", "chargedById"]]
    duration = df["endTime"] - df["startTime"]
    df["duration"] = duration
    df.sort_values(by=["startTime", "duration"], ascending=[True, False], inplace=True)
    daily_grouper = df.groupby(pd.Grouper(key="startTime", freq="D"))
    duration_df = daily_grouper["duration"].sum().reset_index()
    description_df = (
        daily_grouper.apply(lambda x: x.nlargest(4, "duration"))
        .groupby(pd.Grouper(key="startTime", freq="D"))
        .agg(
            {
                "description": lambda x: sorted(
                    list(set(x)),
                    key=lambda d: df.loc[df["description"] == d, "duration"].values[0],
                    reverse=True,
                )
            }
        )
        .reset_index()
    )
    charge_summary = pd.merge(duration_df, description_df, on="startTime")
    date_range = pd.date_range(start=details.start, end=details.end, freq="D")
    date_df = pd.DataFrame({"startTime": date_range})

    period_charge_summary = pd.merge(
        date_df, charge_summary, on="startTime", how="left"
    )
    period_charge_summary["week_number"] = (
        period_charge_summary["startTime"].dt.isocalendar().week
    )
    period_charge_summary["day_number"] = (
        period_charge_summary["startTime"].dt.isocalendar().day
    )
    period_charge_summary["duration"].fillna(timedelta(seconds=0), inplace=True)
    period_charge_summary["description"].fillna("", inplace=True)

    duration_in_seconds = period_charge_summary["duration"].apply(
        lambda x: x.total_seconds()
    )
    period_charge_summary["duration"] = duration_in_seconds
    data = period_charge_summary.to_dict("records")

    calendar_data, weekly_duration = generate_calendar_table(data)
    timesheet_period = f"{details.start.strftime('%d/%m/%Y')} - {details.end.strftime('%d/%m/%Y')} | {(details.end - details.start).days + 1} day(s)"
    pdf_data = {
        "calendar_data": calendar_data,
        "weekly_duration": weekly_duration,
        "timesheet_period": timesheet_period,
        "work_order": work_order.dict(),
    }

    pdf_options = {
        "page-size": "A4",
        "margin-top": "0.05in",
        "margin-right": "0.05in",
        "margin-bottom": "0.3in",
        "margin-left": "0.05in",
        "encoding": "UTF-8",
        "footer-left": "#[page]",
        "footer-right": f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M:%S +00:00/UTC')}",
        "footer-font-size": "8",
        "orientation": "Landscape",
    }

    pdf = generate_timesheet_pdf(
        pdf_options=pdf_options,
        data=pdf_data,
        template="templates/timesheet.html",
    )

    total_time_charged = format_seconds_to_hr_mm(
        period_charge_summary["duration"].sum()
    )

    return total_time_charged, pdf
