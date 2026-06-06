
import os

def skeletonize_project(root_dir="."):
    print(f"Skeletonizing project root: {os.path.abspath(root_dir)}")
    for root, dirs, files in os.walk(root_dir):
        # Skip node_modules, venv, .git, etc.
        if any(skip in root for skip in ["node_modules", "venv", ".git", "__pycache__", ".hermes"]):
            continue
            
        print(f"\nDirectory: {root}")
        for file in files:
            if file.endswith(".py") or file.endswith(".md") or file.endswith(".json") or file.endswith(".txt"):
                print(f"  [FILE] {file}")
            elif os.path.isfile(os.path.join(root, file)):
                # We don't list every single file in node_modules, but we see the structure
                pass

if __name__ == "__main__":
    skeletonize_project()
