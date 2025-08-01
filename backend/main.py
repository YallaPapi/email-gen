import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from tasks import process_spreadsheet_task
import redis

Path("./uploads").mkdir(exist_ok=True)
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_status_db = {}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_path = Path("frontend/index.html")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=html_path.read_text())

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Validate file extension
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_ext} not allowed. Please upload CSV or Excel files only."
        )
    
    # Validate file size (10MB limit)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    max_size = 50 * 1024 * 1024  # 50MB
    
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is 50MB."
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty."
        )
    
    try:
        job_id = str(uuid.uuid4())
        # Sanitize filename - use only UUID and original extension
        safe_filename = f"{job_id}{file_ext}"
        file_location = f"uploads/{safe_filename}"
        
        # Use chunked reading for better memory usage
        with open(file_location, "wb") as f:
            while chunk := file.file.read(8192):  # 8KB chunks
                f.write(chunk)
        
        # Queue the task
        task = process_spreadsheet_task.delay(file_location, job_id)
        job_status_db[job_id] = {
            "status": "QUEUED", 
            "progress": 0, 
            "total": 0, 
            "result_file": None,
            "original_filename": file.filename
        }
        return {"job_id": job_id, "status": "QUEUED"}
    except Exception as e:
        # Clean up file if error occurs
        if 'file_location' in locals() and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/status/{job_id}")
async def get_task_status(job_id: str):
    if job_id not in job_status_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check status file
    status_file = Path(f"uploads/{job_id}_status.txt")
    if status_file.exists():
        status_text = status_file.read_text()
        parts = status_text.split(',')
        if len(parts) == 3:
            status, progress, total = parts
            job_status_db[job_id]['status'] = status
            job_status_db[job_id]['total'] = int(total)
    
    # Check progress in Redis for real-time updates
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        progress = r.get(f"progress_{job_id}")
        if progress:
            job_status_db[job_id]['progress'] = int(progress)
    except:
        pass
    
    # Check if result file exists
    result_file_path = f"uploads/result_{job_id}.xlsx"
    if Path(result_file_path).exists():
        job_status_db[job_id]['status'] = "SUCCESS"
        job_status_db[job_id]['result_file'] = result_file_path
        job_status_db[job_id]['progress'] = job_status_db[job_id]['total']
    
    return job_status_db[job_id]

@app.get("/download/{job_id}")
async def download_result(job_id: str):
    result_file_path = f"uploads/result_{job_id}.xlsx"
    if not os.path.exists(result_file_path):
        raise HTTPException(status_code=404, detail="Result file not found.")
    return FileResponse(path=result_file_path, filename=f"result_{job_id}.xlsx")