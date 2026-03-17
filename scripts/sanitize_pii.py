import re
import os
import json

# Configuration
TARGET_DIRS = ['data', 'init-db', 'backend/tests']
FILE_EXTENSIONS = ['.json', '.sql', '.xml', '.txt']

# Regex Patterns for PII
PII_PATTERNS = {
    'Email': r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
    'CreditCard': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    'Phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
}

def mask_match(match, label):
    """Redacts the match while preserving some context if useful."""
    val = match.group(0)
    if label == 'Email':
        parts = val.split('@')
        return f"{parts[0][0]}***@{parts[1]}"
    if label == 'CreditCard':
        return f"****-****-****-XXXX"
    return f"[REDACTED_{label.upper()}]"

def sanitize_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    original_content = content
    for label, pattern in PII_PATTERNS.items():
        # Specifically targeting realistic data patterns to avoid false positives in code
        content = re.sub(pattern, lambda m: mask_match(m, label), content)

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    modified_count = 0
    for target_dir in TARGET_DIRS:
        if not os.path.exists(target_dir):
            continue
        for root, _, files in os.walk(target_dir):
            for file in files:
                if any(file.endswith(ext) for ext in FILE_EXTENSIONS):
                    if sanitize_file(os.path.join(root, file)):
                        modified_count += 1
    
    print(f"\nSanitization complete. {modified_count} files modified.")

if __name__ == "__main__":
    main()
