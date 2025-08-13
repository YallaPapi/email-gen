#!/usr/bin/env python3
"""Minimal test server to verify HTML serving works"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    html_path = Path("frontend/index.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    else:
        return {"error": "Frontend not found", "looked_in": str(html_path.absolute())}

if __name__ == "__main__":
    print("Starting test server on http://localhost:8002")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=8002)