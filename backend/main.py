import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from tasks import process_spreadsheet_task, celery_app, update_status
import redis
import pandas as pd

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

def initialize_job_status_db():
    """Initialize job_status_db from existing files on server startup"""
    global job_status_db
    
    try:
        uploads_path = Path("uploads")
        if not uploads_path.exists():
            return
            
        # Get all UUID-like files (job files)
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(csv|xlsx|xls)$')
        
        for file_path in uploads_path.iterdir():
            if file_path.is_file() and uuid_pattern.match(file_path.name):
                job_id = file_path.stem  # Remove extension to get job_id
                
                # Try to read CSV/Excel to get original filename
                original_filename = "Unknown"
                mode = "single"
                total_rows = 0
                
                try:
                    if file_path.suffix.lower() == '.csv':
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)
                    total_rows = len(df)
                    original_filename = f"recovered_{file_path.name}"
                    
                    # Check if it's a sequence job by looking for email columns
                    if 'initial_email' in df.columns and 'followup_1' in df.columns:
                        mode = "sequence"
                        
                except Exception:
                    pass
                
                # Check status file
                status = "UNKNOWN"
                progress = 0
                status_file = uploads_path / f"{job_id}_status.txt"
                if status_file.exists():
                    try:
                        status_text = status_file.read_text().strip()
                        parts = status_text.split(',')
                        if len(parts) == 3:
                            status, progress, total_rows = parts
                            progress = int(progress)
                            total_rows = int(total_rows)
                    except Exception:
                        pass
                
                # Check if result file exists
                result_file_path = f"uploads/result_{job_id}.xlsx"
                csv_result_path = f"uploads/result_{job_id}.csv"
                if os.path.exists(result_file_path) or os.path.exists(csv_result_path):
                    status = "SUCCESS"
                    progress = total_rows
                
                # Add to job_status_db
                job_status_db[job_id] = {
                    "status": status,
                    "progress": progress,
                    "total": total_rows,
                    "result_file": result_file_path if os.path.exists(result_file_path) else csv_result_path if os.path.exists(csv_result_path) else None,
                    "original_filename": original_filename,
                    "mode": mode
                }
                
        print(f"Initialized job_status_db with {len(job_status_db)} existing jobs")
        
    except Exception as e:
        print(f"Error initializing job_status_db: {e}")

# Initialize on startup
initialize_job_status_db()

@app.get("/")
async def serve_frontend():
    """Return the actual index.html file"""
    try:
        html_path = "/app/index.html"
        if not os.path.exists(html_path):
            html_path = "index.html"
        return FileResponse(html_path, media_type="text/html")
    except Exception as e:
        return HTMLResponse(f"<h1>Error loading index.html: {str(e)}</h1><p>Current directory: {os.getcwd()}</p><p>Files: {os.listdir('.')}</p>", status_code=500)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), mode: str = Form("single")):
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type {file_ext} not allowed")
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    max_size = 50 * 1024 * 1024
    
    if file_size > max_size:
        raise HTTPException(status_code=400, detail="File too large")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    try:
        job_id = str(uuid.uuid4())
        safe_filename = f"{job_id}{file_ext}"
        file_location = f"uploads/{safe_filename}"
        
        with open(file_location, "wb") as f:
            while chunk := file.file.read(8192):
                f.write(chunk)
        
        task = process_spreadsheet_task.delay(file_location, job_id, mode)
        job_status_db[job_id] = {
            "status": "QUEUED", 
            "progress": 0, 
            "total": 0, 
            "result_file": None,
            "original_filename": file.filename,
            "mode": mode
        }
        return {"job_id": job_id, "status": "QUEUED"}
    except Exception as e:
        if 'file_location' in locals() and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/status/{job_id}")
async def get_task_status(job_id: str):
    if job_id not in job_status_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status_file = Path(f"uploads/{job_id}_status.txt")
    if status_file.exists():
        status_text = status_file.read_text().strip()
        parts = status_text.split(',')
        if len(parts) == 3:
            status, progress, total = parts
            job_status_db[job_id]['status'] = status
            job_status_db[job_id]['progress'] = int(progress)
            job_status_db[job_id]['total'] = int(total)
    
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        redis_progress = r.get(f"progress_{job_id}")
        redis_total = r.get(f"total_{job_id}")
        if redis_progress:
            job_status_db[job_id]['progress'] = int(redis_progress)
        if redis_total:
            job_status_db[job_id]['total'] = int(redis_total)
    except:
        pass
    
    result_file_path = f"uploads/result_{job_id}.xlsx"
    if Path(result_file_path).exists():
        job_status_db[job_id]['status'] = "SUCCESS"
        job_status_db[job_id]['result_file'] = result_file_path
        job_status_db[job_id]['progress'] = job_status_db[job_id]['total']
    
    return job_status_db[job_id]

@app.get("/download/{job_id}")
async def download_result(job_id: str):
    result_file_path = f"uploads/result_{job_id}.xlsx"
    csv_file_path = f"uploads/result_{job_id}.csv"
    
    if os.path.exists(result_file_path):
        return FileResponse(path=result_file_path, filename=f"result_{job_id}.xlsx")
    elif os.path.exists(csv_file_path):
        return FileResponse(path=csv_file_path, filename=f"result_{job_id}.csv")
    
    raise HTTPException(status_code=404, detail="Result file not found")

@app.get("/jobs")
async def get_all_jobs():
    """Get all jobs with their current status"""
    try:
        # If job_status_db is empty or has very few entries, reinitialize from filesystem
        if len(job_status_db) < 5:  # Threshold to trigger rebuild
            initialize_job_status_db()
        
        jobs = []
        for job_id, job_data in job_status_db.items():
            # Check if result file exists
            result_file_xlsx = f"uploads/result_{job_id}.xlsx" 
            result_file_csv = f"uploads/result_{job_id}.csv"
            has_result = os.path.exists(result_file_xlsx) or os.path.exists(result_file_csv)
            
            # Get upload time from file creation if available
            input_files = [f for f in os.listdir("uploads") if f.startswith(job_id) and not f.endswith("_status.txt")]
            upload_time = None
            if input_files:
                file_path = f"uploads/{input_files[0]}"
                if os.path.exists(file_path):
                    upload_time = os.path.getctime(file_path)
            
            jobs.append({
                "job_id": job_id,
                "status": job_data.get("status", "UNKNOWN"),
                "progress": job_data.get("progress", 0),
                "total": job_data.get("total", 0),
                "original_filename": job_data.get("original_filename", "Unknown"),
                "mode": job_data.get("mode", "single"),
                "has_result": has_result,
                "download_url": f"/download/{job_id}" if has_result else None,
                "upload_time": upload_time
            })
        
        # Sort by upload time, most recent first
        jobs.sort(key=lambda x: x.get("upload_time", 0), reverse=True)
        
        return {"jobs": jobs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")

@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    if job_id not in job_status_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        # Update status to cancelled
        job_status_db[job_id]["status"] = "CANCELLED"
        update_status(job_id, "CANCELLED", 0, 0)
        
        # Try to revoke the Celery task if it exists
        try:
            from celery import current_app
            current_app.control.revoke(job_id, terminate=True)
        except:
            pass  # Continue even if revoke fails
        
        return {"message": "Job cancelled successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling job: {str(e)}")

@app.delete("/delete/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files"""
    if job_id not in job_status_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        # Remove from memory
        del job_status_db[job_id]
        
        # Remove associated files
        files_to_remove = [
            f"uploads/{job_id}.csv",
            f"uploads/{job_id}.xlsx", 
            f"uploads/{job_id}_status.txt",
            f"uploads/result_{job_id}.xlsx",
            f"uploads/result_{job_id}.csv"
        ]
        
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Remove from Redis
        try:
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            r.delete(f"progress_{job_id}")
            r.delete(f"total_{job_id}")
        except:
            pass
        
        return {"message": "Job deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")

@app.post("/refresh-jobs")
async def refresh_jobs():
    """Force refresh job history from filesystem"""
    try:
        initialize_job_status_db()
        return {"message": f"Job history refreshed. Found {len(job_status_db)} jobs."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing jobs: {str(e)}")