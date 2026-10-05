import os

print("Searching for any .db files in the project workspace:")
for root, dirs, files in os.walk("."):
    if "venv" in root or "node_modules" in root or ".git" in root:
        continue
    for file in files:
        if file.endswith(".db"):
            print(f" -> Found: {os.path.join(root, file)}")