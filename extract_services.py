import re

with open("backend/main.py", "r") as f:
    text = f.read()

functions_to_extract = [
    r"async def _validate_p2p_transfer[\s\S]*?(?=\nasync def _execute_p2p_balances)",
    r"async def _execute_p2p_balances[\s\S]*?(?=\ndef _create_p2p_transactions)",
    r"def _create_p2p_transactions[\s\S]*?(?=\ndef _create_p2p_outbox_entries)",
    r"def _create_p2p_outbox_entries[\s\S]*?(?=\nSIMULATOR_URL = )",
    r"SIMULATOR_URL = os\.getenv\(\"SIMULATOR_URL\"\)\nSIMULATOR_API_KEY = os\.getenv\(\"SIMULATOR_API_KEY\"\)\n\nasync def get_vendors[\s\S]*?(?=\nasync def execute_vendor_payment_immediate)",
    r"async def execute_vendor_payment_immediate[\s\S]*?(?=\n@app\.post\(\"/p2p-transfer\"\))",
    r"def _calculate_next_run_at[\s\S]*?(?=\n@app\.post\(\"/v1/transfers/scheduled\"\))"
]

extracted_blocks = []
for pattern in functions_to_extract:
    match = re.search(pattern, text)
    if match:
        extracted_blocks.append(match.group(0))
        text = text.replace(match.group(0), "")
    else:
        print("Failed to match:", pattern[:30])

header = """import os
import uuid
import datetime
from decimal import Decimal
from typing import Optional, Tuple
import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import User, Account, Transaction, Outbox

"""

with open("backend/services/transfer_service.py", "w") as f:
    f.write(header + "\n\n".join(extracted_blocks) + "\n")

text = text.replace("from sync_checker import run_sync_check", "from sync_checker import run_sync_check\nfrom services.transfer_service import _validate_p2p_transfer, _execute_p2p_balances, _create_p2p_transactions, _create_p2p_outbox_entries, get_vendors, execute_vendor_payment_immediate, _calculate_next_run_at\n")

with open("backend/main.py", "w") as f:
    f.write(text)
