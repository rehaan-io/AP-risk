import re
import os

with open("backend/main.py", "r") as f:
    content = f.read()

# Replace CORS
new_cors = """import os
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "AP Risk Intelligence Backend is running"}"""

content = re.sub(
    r'app\.add_middleware\(\s*CORSMiddleware,\s*allow_origins=\["\*"\](?:.|\n)*?allow_headers=\["\*"\]\s*,\s*\)',
    new_cors,
    content
)

with open("backend/main.py", "w") as f:
    f.write(content)
