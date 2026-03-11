import re

# 1. contacts.py
with open("backend/routers/contacts.py", "r") as f:
    text = f.read()
text = text.replace("from sqlalchemy.orm import Session", "")
text = text.replace("from sqlalchemy.ext.asyncio import AsyncSession", "from sqlalchemy.ext.asyncio import AsyncSession\nfrom sqlalchemy.orm import Session")
with open("backend/routers/contacts.py", "w") as f:
    f.write(text)

# 2. transfers.py
with open("backend/routers/transfers.py", "r") as f:
    text = f.read()
text = text.replace("from decimal import Decimal", "from decimal import Decimal\nfrom sqlalchemy.exc import SQLAlchemyError\nfrom security_checks import check_velocity, check_anomaly")
with open("backend/routers/transfers.py", "w") as f:
    f.write(text)

# 3. dashboard.py
with open("backend/routers/dashboard.py", "r") as f:
    text = f.read()
text = text.replace("from typing import Dict, Any, List", "from typing import Dict, Any, List, Optional")
text = text.replace("from sqlalchemy.ext.asyncio import AsyncSession", "from sqlalchemy.ext.asyncio import AsyncSession\nfrom sqlalchemy.orm import Session")
with open("backend/routers/dashboard.py", "w") as f:
    f.write(text)

# 4. vendors.py
with open("backend/routers/vendors.py", "r") as f:
    text = f.read()
# Cut out everything from @router.get("/v1/admin/banking-metrics")
m = re.search(r"@router\.get\(\"/v1/admin/banking-metrics\"\)[\s\S]*", text)
if m:
    text = text.replace(m.group(0), "")
with open("backend/routers/vendors.py", "w") as f:
    f.write(text)

