import os
import glob
import re

for test_file in glob.glob("backend/tests/*.py") + glob.glob("tests/*.py"):
    with open(test_file, 'r') as f:
        content = f.read()

    content = content.replace("from backend.routers import admin", "from routers import admin")
    content = content.replace("from backend.routers import transfers", "from routers import transfers")

    with open(test_file, 'w') as f:
        f.write(content)

