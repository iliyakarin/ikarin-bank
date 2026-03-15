
import re
import os

def get_env_vars(filepath):
    vars = set()
    if not os.path.exists(filepath):
        print(f"Warning: File not found: {filepath}")
        return vars
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                match = re.match(r'^([^=]+)=', line)
                if match:
                    vars.add(match.group(1))
    return vars

# Use relative paths or handle the WSL path correctly
base_path = "."
dev_vars = get_env_vars(os.path.join(base_path, '.env.dev'))
prod_vars = get_env_vars(os.path.join(base_path, '.env.prod'))

# Read development.md
doc_path = os.path.join(base_path, '.claude/guidelines/development.md')
with open(doc_path, 'r') as f:
    doc_content = f.read()

# Extract variables from the code block in development.md
doc_vars = set()
match = re.search(r'Required keys:\s*```\s*(.*?)\s*```', doc_content, re.DOTALL)
if match:
    variables_text = match.group(1)
    # Split by commas and newlines
    for v in re.split(r'[,\s\n]+', variables_text):
        v = v.strip().replace(',', '')
        if v:
            doc_vars.add(v)

all_env_vars = dev_vars.union(prod_vars)

missing_in_doc = all_env_vars - doc_vars
extra_in_doc = doc_vars - all_env_vars

print(f"Total variables in .env files: {len(all_env_vars)}")
print(f"Total variables identified in documentation: {len(doc_vars)}")

print("\n### Missing in documentation:")
if not missing_in_doc:
    print("None!")
for v in sorted(missing_in_doc):
    print(f"- {v}")

print("\n### Extra in documentation (not in .env files):")
if not extra_in_doc:
    print("None!")
for v in sorted(extra_in_doc):
    print(f"- {v}")

# Look for potential name mismatches
if 'JWT_SECRET_KEY' in doc_vars and 'SECRET_KEY' in all_env_vars:
    print("\n### Potential Naming Mismatch:")
    print("- Documentation says `JWT_SECRET_KEY`, but .env files use `SECRET_KEY`")

if 'JWT_ALGORITHM' in doc_vars and 'JWT_ALGORITHM' not in all_env_vars:
    print("- `JWT_ALGORITHM` is in documentation but missing from .env files")

if 'ACCESS_TOKEN_EXPIRE_MINUTES' in doc_vars and 'ACCESS_TOKEN_EXPIRE_MINUTES' not in all_env_vars:
    print("- `ACCESS_TOKEN_EXPIRE_MINUTES` is in documentation but missing from .env files")
