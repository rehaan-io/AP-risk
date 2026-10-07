import os
import glob
import re

frontend_dir = "frontend/src"

for root, _, files in os.walk(frontend_dir):
    for file in files:
        if file.endswith(".tsx") or file.endswith(".ts"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if "http://localhost:8000" in content:
                # Replace backtick enclosed strings
                content = re.sub(
                    r'`http://localhost:8000(/?.*?)`', 
                    r'`${import.meta.env.VITE_API_URL}\1`', 
                    content
                )
                # Replace single quote enclosed strings
                content = re.sub(
                    r"'http://localhost:8000(/?.*?)'", 
                    r'`${import.meta.env.VITE_API_URL}\1`', 
                    content
                )
                # Replace double quote enclosed strings
                content = re.sub(
                    r'"http://localhost:8000(/?.*?)"', 
                    r'`${import.meta.env.VITE_API_URL}\1`', 
                    content
                )
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Updated {filepath}")
