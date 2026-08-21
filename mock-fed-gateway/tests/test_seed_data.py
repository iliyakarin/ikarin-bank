import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from seed_data import FED_DISTRICTS_DATA, INSTITUTIONS_DATA
from routing_utils import validate_routing_number

def test_districts_data_count_and_keys():
    assert len(FED_DISTRICTS_DATA) == 12
    codes = [d["code"] for d in FED_DISTRICTS_DATA]
    assert sorted(codes) == [f"{i:02d}" for i in range(1, 13)]
    for d in FED_DISTRICTS_DATA:
        assert "name" in d
        assert "district_letter" in d
        assert "head_office_city" in d
        assert "head_office_state" in d

def test_all_institutions_have_valid_routing_checksums():
    assert len(INSTITUTIONS_DATA) >= 30
    for inst in INSTITUTIONS_DATA:
        res = validate_routing_number(inst["routing_number"])
        assert res["valid"] is True, f"Institution {inst['name']} has invalid RTN: {inst['routing_number']} error: {res['errors']}"
        assert inst["district_id"] >= 1 and inst["district_id"] <= 12
        assert "name" in inst
        assert "short_name" in inst
        assert "city" in inst
        assert "state" in inst
