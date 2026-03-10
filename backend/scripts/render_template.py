import os
import re
from dotenv import load_dotenv

def render(template_path, env_file):
    if not os.path.exists(template_path):
        print(f"Error: {template_path} not found")
        return
    if not os.path.exists(env_file):
        print(f"Error: {env_file} not found")
        return
    
    load_dotenv(env_file)
    with open(template_path, "r") as f:
        content = f.read()

    # Find all ${VAR} and replace
    placeholders = re.findall(r"\${(\w+)}", content)
    missing = []
    for ph in placeholders:
        val = os.getenv(ph)
        if not val:
            missing.append(ph)
        else:
            content = content.replace(f"${{{ph}}}", val)

    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        return

    output_path = template_path.replace(".template", "")
    with open(output_path, "w") as f:
        f.write(content)
    print(f"Successfully rendered {output_path} from {template_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 render_template.py <template_path> <env_file_path>")
        sys.exit(1)
    t = sys.argv[1]
    e = sys.argv[2]
    render(t, e)
