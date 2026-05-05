import datetime
from typing import Optional, Any
from dateutil.relativedelta import relativedelta

def add_one_month(dt: datetime.datetime) -> datetime.datetime:
    """Safely adds one month to a datetime object."""
    return dt + relativedelta(months=1)

def get_next_weekday(dt: datetime.datetime, weekday_name: str) -> Optional[datetime.datetime]:
    """Calculates the next occurrence of a specific weekday."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if weekday_name not in days:
        return None
    target_day = days.index(weekday_name)
    days_ahead = target_day - dt.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return dt + datetime.timedelta(days=days_ahead)

def get_next_specific_date(dt: datetime.datetime, target_day_str: str) -> Optional[datetime.datetime]:
    """Calculates the next occurrence of a specific day of the month."""
    try:
        target_day = int(target_day_str)
        # Always try next month for scheduled recurring logic (baseline logic from transfer_service)
        return add_one_month(dt.replace(day=1)).replace(day=1) + datetime.timedelta(days=min(target_day, 28)-1)
    except ValueError:
        return None

def calculate_next_run_at(reference_date: datetime.datetime, frequency: str, interval: Any = None) -> Optional[datetime.datetime]:
    """Calculates the next execution date based on frequency strings."""
    if frequency == "One-time": 
        return None
    
    if frequency == "Daily": 
        return reference_date + datetime.timedelta(days=1)
    if frequency == "Weekly": 
        return reference_date + datetime.timedelta(weeks=1)
    if frequency == "Bi-weekly": 
        return reference_date + datetime.timedelta(weeks=2)
    
    if frequency == "Monthly":
        return add_one_month(reference_date)
    
    if frequency == "Specific Day of Week" and interval:
        return get_next_weekday(reference_date, interval)
            
    if frequency == "Specific Date of Month" and interval:
        return get_next_specific_date(reference_date, interval)

    return None
