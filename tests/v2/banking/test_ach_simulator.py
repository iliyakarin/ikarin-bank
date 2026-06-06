import pytest
import datetime
import pytz
from v2.banking.ach_simulator import ACHSimulator

def test_ach_settlement_window():
    sim = ACHSimulator()
    # 10:00 AM ET
    dt_morning = datetime.datetime(2024, 1, 1, 10, 0, tzinfo=pytz.timezone("US/Eastern"))
    # 6:00 PM ET
    dt_evening = datetime.datetime(2024, 1, 1, 18, 0, tzinfo=pytz.timezone("US/Eastern"))
    
    assert sim.is_within_settlement_window(dt_morning) is True
    assert sim.is_within_settlement_window(dt_evening) is False

def test_ach_business_day():
    sim = ACHSimulator()
    monday = datetime.datetime(2024, 1, 1, 12, 0)
    sunday = datetime.datetime(2024, 1, 7, 12, 0)
    
    assert sim.is_business_day(monday) is True
    assert sim.is_business_day(sunday) is False
