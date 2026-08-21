from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import FederalReserveDistrict, Institution, MasterAccount

FED_DISTRICTS_DATA: List[Dict[str, Any]] = [
    {"id": 1, "code": "01", "name": "Federal Reserve Bank of Boston", "district_letter": "A", "head_office_city": "Boston", "head_office_state": "MA", "routing_prefix_ranges": ["01", "21"]},
    {"id": 2, "code": "02", "name": "Federal Reserve Bank of New York", "district_letter": "B", "head_office_city": "New York", "head_office_state": "NY", "routing_prefix_ranges": ["02", "22"]},
    {"id": 3, "code": "03", "name": "Federal Reserve Bank of Philadelphia", "district_letter": "C", "head_office_city": "Philadelphia", "head_office_state": "PA", "routing_prefix_ranges": ["03", "23", "30", "31", "32"]},
    {"id": 4, "code": "04", "name": "Federal Reserve Bank of Cleveland", "district_letter": "D", "head_office_city": "Cleveland", "head_office_state": "OH", "routing_prefix_ranges": ["04", "24"]},
    {"id": 5, "code": "05", "name": "Federal Reserve Bank of Richmond", "district_letter": "E", "head_office_city": "Richmond", "head_office_state": "VA", "routing_prefix_ranges": ["05", "25"]},
    {"id": 6, "code": "06", "name": "Federal Reserve Bank of Atlanta", "district_letter": "F", "head_office_city": "Atlanta", "head_office_state": "GA", "routing_prefix_ranges": ["06", "26"]},
    {"id": 7, "code": "07", "name": "Federal Reserve Bank of Chicago", "district_letter": "G", "head_office_city": "Chicago", "head_office_state": "IL", "routing_prefix_ranges": ["07", "27"]},
    {"id": 8, "code": "08", "name": "Federal Reserve Bank of St. Louis", "district_letter": "H", "head_office_city": "St. Louis", "head_office_state": "MO", "routing_prefix_ranges": ["08", "28", "80"]},
    {"id": 9, "code": "09", "name": "Federal Reserve Bank of Minneapolis", "district_letter": "I", "head_office_city": "Minneapolis", "head_office_state": "MN", "routing_prefix_ranges": ["09", "29"]},
    {"id": 10, "code": "10", "name": "Federal Reserve Bank of Kansas City", "district_letter": "J", "head_office_city": "Kansas City", "head_office_state": "MO", "routing_prefix_ranges": ["10", "30"]},
    {"id": 11, "code": "11", "name": "Federal Reserve Bank of Dallas", "district_letter": "K", "head_office_city": "Dallas", "head_office_state": "TX", "routing_prefix_ranges": ["11", "31", "70", "71", "72"]},
    {"id": 12, "code": "12", "name": "Federal Reserve Bank of San Francisco", "district_letter": "L", "head_office_city": "San Francisco", "head_office_state": "CA", "routing_prefix_ranges": ["12", "32", "61", "62", "63", "64", "65", "66", "67", "68", "69", "90", "91", "92"]},
]

INSTITUTIONS_DATA: List[Dict[str, Any]] = [
    # Karin Bank Node
    {"routing_number": "123456780", "name": "Karin Bank, N.A.", "short_name": "KARIN SFO", "district_id": 12, "office_code": "O", "servicing_frb_number": "121000019", "address": "100 California St", "city": "San Francisco", "state": "CA", "zip_code": "94111", "phone": "415-555-0100", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "111000025", "name": "Karin Bank Austin Operations", "short_name": "KARIN ATX", "district_id": 11, "office_code": "B", "servicing_frb_number": "111000012", "address": "500 Congress Ave", "city": "Austin", "state": "TX", "zip_code": "78701", "phone": "512-555-0140", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    # Top US Banks
    {"routing_number": "021000021", "name": "JPMorgan Chase Bank, N.A.", "short_name": "CHASE NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "270 Park Ave", "city": "New York", "state": "NY", "zip_code": "10017", "phone": "212-270-6000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "122241255", "name": "JPMorgan Chase Bank (California)", "short_name": "CHASE LA", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "1999 Avenue of the Stars", "city": "Los Angeles", "state": "CA", "zip_code": "90067", "phone": "310-860-7000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "071000013", "name": "JPMorgan Chase Bank (Chicago)", "short_name": "CHASE CHI", "district_id": 7, "office_code": "B", "servicing_frb_number": "071000301", "address": "10 S Dearborn St", "city": "Chicago", "state": "IL", "zip_code": "60603", "phone": "312-732-4000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "111000012", "name": "Bank of America, N.A. (Texas)", "short_name": "BOA DAL", "district_id": 11, "office_code": "B", "servicing_frb_number": "111000012", "address": "901 Main St", "city": "Dallas", "state": "TX", "zip_code": "75202", "phone": "214-209-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "121000358", "name": "Bank of America, N.A. (California)", "short_name": "BOA SFO", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "333 S Hope St", "city": "Los Angeles", "state": "CA", "zip_code": "90071", "phone": "213-345-6789", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "053000196", "name": "Bank of America, N.A. (HQ)", "short_name": "BOA NC", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "100 N Tryon St", "city": "Charlotte", "state": "NC", "zip_code": "28255", "phone": "800-432-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "121000248", "name": "Wells Fargo Bank, N.A.", "short_name": "WELLS SFO", "district_id": 12, "office_code": "O", "servicing_frb_number": "121000019", "address": "420 Montgomery St", "city": "San Francisco", "state": "CA", "zip_code": "94104", "phone": "800-869-3557", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "091000019", "name": "Wells Fargo Bank (Northwest)", "short_name": "WELLS MSP", "district_id": 9, "office_code": "B", "servicing_frb_number": "091000080", "address": "90 S 7th St", "city": "Minneapolis", "state": "MN", "zip_code": "55402", "phone": "612-667-1234", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "102000076", "name": "Wells Fargo Bank (Colorado)", "short_name": "WELLS DEN", "district_id": 10, "office_code": "B", "servicing_frb_number": "102000199", "address": "1700 Lincoln St", "city": "Denver", "state": "CO", "zip_code": "80203", "phone": "303-863-6000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "021000089", "name": "Citibank, N.A.", "short_name": "CITI NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "388 Greenwich St", "city": "New York", "state": "NY", "zip_code": "10013", "phone": "212-559-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "321171184", "name": "Citibank, N.A. (South Dakota)", "short_name": "CITI SD", "district_id": 9, "office_code": "B", "servicing_frb_number": "091000080", "address": "701 E 60th St N", "city": "Sioux Falls", "state": "SD", "zip_code": "57104", "phone": "605-331-2000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "091000022", "name": "U.S. Bank National Association", "short_name": "USBANK MSP", "district_id": 9, "office_code": "O", "servicing_frb_number": "091000080", "address": "800 Nicollet Mall", "city": "Minneapolis", "state": "MN", "zip_code": "55402", "phone": "800-872-2657", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "123000848", "name": "U.S. Bank (Oregon)", "short_name": "USBANK PDX", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "111 SW 5th Ave", "city": "Portland", "state": "OR", "zip_code": "97204", "phone": "503-275-6111", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "043000096", "name": "PNC Bank, National Association", "short_name": "PNC PIT", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "300 Fifth Ave", "city": "Pittsburgh", "state": "PA", "zip_code": "15222", "phone": "888-762-2265", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "071921891", "name": "PNC Bank (Midwest)", "short_name": "PNC CHI", "district_id": 7, "office_code": "B", "servicing_frb_number": "071000301", "address": "1 N Franklin St", "city": "Chicago", "state": "IL", "zip_code": "60606", "phone": "312-384-4000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "061000104", "name": "Truist Bank", "short_name": "TRUIST ATL", "district_id": 6, "office_code": "O", "servicing_frb_number": "061000146", "address": "214 N Tryon St", "city": "Charlotte", "state": "NC", "zip_code": "28202", "phone": "844-487-8478", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "026002561", "name": "Goldman Sachs Bank USA", "short_name": "GS NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "200 West St", "city": "New York", "state": "NY", "zip_code": "10282", "phone": "212-902-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "026013576", "name": "Morgan Stanley Private Bank, N.A.", "short_name": "MS NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "1585 Broadway", "city": "New York", "state": "NY", "zip_code": "10036", "phone": "212-761-4000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "051405515", "name": "Capital One, N.A.", "short_name": "CAPONE VA", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "1680 Capital One Dr", "city": "McLean", "state": "VA", "zip_code": "22102", "phone": "877-383-4802", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "011103093", "name": "TD Bank, N.A.", "short_name": "TD PORT", "district_id": 1, "office_code": "O", "servicing_frb_number": "011000015", "address": "One Portland Square", "city": "Portland", "state": "ME", "zip_code": "04101", "phone": "888-751-9000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "021000018", "name": "The Bank of New York Mellon", "short_name": "BNY MELLON", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "240 Greenwich St", "city": "New York", "state": "NY", "zip_code": "10286", "phone": "212-495-1784", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "011000028", "name": "State Street Bank and Trust Company", "short_name": "STATE STREET", "district_id": 1, "office_code": "O", "servicing_frb_number": "011000015", "address": "1 Lincoln St", "city": "Boston", "state": "MA", "zip_code": "02111", "phone": "617-786-3000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "121202211", "name": "Charles Schwab Bank, SSB", "short_name": "SCHWAB TX", "district_id": 11, "office_code": "O", "servicing_frb_number": "111000012", "address": "3000 Schwab Way", "city": "Westlake", "state": "TX", "zip_code": "76262", "phone": "888-403-9000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "101000695", "name": "UMB Bank, N.A. (Fidelity)", "short_name": "UMB FIDELITY", "district_id": 10, "office_code": "O", "servicing_frb_number": "102000199", "address": "1010 Grand Blvd", "city": "Kansas City", "state": "MO", "zip_code": "64106", "phone": "816-860-7000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    # Credit Unions & Digital
    {"routing_number": "256074974", "name": "Navy Federal Credit Union", "short_name": "NAVY FED", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "820 Follin Ln", "city": "Vienna", "state": "VA", "zip_code": "22180", "phone": "888-842-6328", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "253177094", "name": "State Employees' Credit Union", "short_name": "SECU NC", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "119 N Salisbury St", "city": "Raleigh", "state": "NC", "zip_code": "27603", "phone": "888-732-8562", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": False, "status": "ACTIVE"},
    {"routing_number": "124003116", "name": "Ally Bank", "short_name": "ALLY UT", "district_id": 12, "office_code": "O", "servicing_frb_number": "121000019", "address": "6985 Union Park Center", "city": "Midvale", "state": "UT", "zip_code": "84047", "phone": "877-247-2559", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "121140399", "name": "Silicon Valley Bank (First-Citizens)", "short_name": "SVB FCB", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "3003 Tasman Dr", "city": "Santa Clara", "state": "CA", "zip_code": "95054", "phone": "800-774-7390", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "022000046", "name": "M&T Bank", "short_name": "M&T BUF", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "One M&T Plaza", "city": "Buffalo", "state": "NY", "zip_code": "14203", "phone": "800-724-2440", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "042000314", "name": "Fifth Third Bank, National Association", "short_name": "53 CIN", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "38 Fountain Sq Plaza", "city": "Cincinnati", "state": "OH", "zip_code": "45263", "phone": "800-972-3030", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "041001039", "name": "KeyBank National Association", "short_name": "KEYBANK CLE", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "127 Public Sq", "city": "Cleveland", "state": "OH", "zip_code": "44114", "phone": "800-539-2968", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "011500120", "name": "Citizens Bank, N.A.", "short_name": "CITIZENS RI", "district_id": 1, "office_code": "O", "servicing_frb_number": "011000015", "address": "One Citizens Plaza", "city": "Providence", "state": "RI", "zip_code": "02903", "phone": "800-922-9999", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "062000019", "name": "Regions Bank", "short_name": "REGIONS BHM", "district_id": 6, "office_code": "O", "servicing_frb_number": "061000146", "address": "1900 5th Ave N", "city": "Birmingham", "state": "AL", "zip_code": "35203", "phone": "800-734-4667", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "044000024", "name": "The Huntington National Bank", "short_name": "HUNTINGTON OH", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "41 S High St", "city": "Columbus", "state": "OH", "zip_code": "43215", "phone": "800-480-2265", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "071000288", "name": "BMO Bank National Association", "short_name": "BMO CHI", "district_id": 7, "office_code": "O", "servicing_frb_number": "071000301", "address": "320 S Canal St", "city": "Chicago", "state": "IL", "zip_code": "60606", "phone": "888-340-2265", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
]

async def seed_all_data(session: AsyncSession) -> Dict[str, int]:
    # 1. Seed Districts
    res = await session.execute(select(FederalReserveDistrict))
    existing_districts = {d.id: d for d in res.scalars().all()}
    districts_added = 0
    for d in FED_DISTRICTS_DATA:
        if d["id"] not in existing_districts:
            session.add(FederalReserveDistrict(**d))
            districts_added += 1
    await session.flush()

    # 2. Seed Institutions
    res = await session.execute(select(Institution))
    existing_inst = {inst.routing_number: inst for inst in res.scalars().all()}
    institutions_added = 0
    for inst in INSTITUTIONS_DATA:
        if inst["routing_number"] not in existing_inst:
            session.add(Institution(**inst))
            institutions_added += 1
    await session.flush()

    # 3. Seed Master Accounts
    res = await session.execute(select(Institution))
    all_insts = res.scalars().all()
    res = await session.execute(select(MasterAccount))
    existing_accounts = {ma.routing_number: ma for ma in res.scalars().all()}
    accounts_added = 0
    for inst in all_insts:
        if inst.routing_number not in existing_accounts:
            acct_num = f"FRB-{inst.routing_number}-01"
            session.add(MasterAccount(
                account_number=acct_num,
                routing_number=inst.routing_number,
                currency="USD",
                balance_cents=1_000_000_000,
                daylight_overdraft_limit_cents=500_000_000,
                status="OPEN",
            ))
            accounts_added += 1
    
    await session.commit()
    return {
        "districts_added": districts_added,
        "institutions_added": institutions_added,
        "accounts_added": accounts_added,
    }
