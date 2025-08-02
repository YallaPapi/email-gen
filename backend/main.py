import os
import uuid
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from tasks import process_spreadsheet_task, celery_app, update_status
import redis
from worker_models import WorkerModelAssigner
from datetime import datetime
import json
import pickle
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

async def attempt_recovery(job_id: str):
    """Attempt to recover generated emails from Redis when combine step failed"""
    try:
        print(f"Attempting recovery for job {job_id}")
        
        # Connect to Redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        
        # Check if there's a progress counter indicating work was done
        progress_key = f"progress_{job_id}"
        progress = r.get(progress_key)
        if not progress:
            print(f"No progress found for {job_id}")
            return None
        
        progress_count = int(progress)
        if progress_count == 0:
            print(f"No emails processed for {job_id}")
            return None
        
        print(f"Found {progress_count} processed emails for {job_id}, recovering...")
        
        # Get all Celery task result keys
        task_keys = r.keys("celery-task-meta-*")
        recovered_results = []
        
        for key in task_keys:
            try:
                raw_result = r.get(key)
                if not raw_result:
                    continue
                
                # Try to deserialize the result
                try:
                    result_data = pickle.loads(raw_result)
                except:
                    try:
                        result_data = json.loads(raw_result.decode('utf-8'))
                    except:
                        continue
                
                # Look for email generation results
                if isinstance(result_data, dict) and 'result' in result_data:
                    result = result_data['result']
                    if isinstance(result, dict) and 'row_data' in result and 'email' in result:
                        recovered_results.append(result)
                        
            except Exception:
                continue
        
        if not recovered_results:
            print(f"No recoverable email results found for {job_id}")
            return None
        
        print(f"Recovered {len(recovered_results)} email results")
        
        # Sort by index to maintain order
        recovered_results.sort(key=lambda x: x.get('index', 0))
        
        # Build final dataframe
        final_data = []
        for result in recovered_results:
            row = result['row_data'].copy()
            
            # Clean email text
            email_text = result['email']
            if isinstance(email_text, str):
                email_text = email_text.replace('\x00', '').replace('\x01', '').replace('\x02', '')
                email_text = ''.join(char for char in email_text if ord(char) >= 32 or char in '\n\r\t')
            
            row['generated_email'] = email_text
            row['model_used'] = result.get('model_used', 'unknown')
            row['recovery_status'] = 'recovered'
            final_data.append(row)
        
        # Save recovered data
        df = pd.DataFrame(final_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"uploads/RECOVERED_{job_id}_{timestamp}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"Recovery successful: {len(final_data)} emails saved to {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Recovery error for {job_id}: {e}")
        return None

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
    csv_file_path = f"uploads/result_{job_id}.csv"
    
    # Check if result file exists
    if os.path.exists(result_file_path):
        return FileResponse(path=result_file_path, filename=f"result_{job_id}.xlsx")
    elif os.path.exists(csv_file_path):
        return FileResponse(path=csv_file_path, filename=f"result_{job_id}.csv")
    
    # Try recovery from Redis if no result file exists
    try:
        recovered_file = await attempt_recovery(job_id)
        if recovered_file:
            filename = os.path.basename(recovered_file)
            return FileResponse(path=recovered_file, filename=filename)
    except Exception as e:
        print(f"Recovery failed for {job_id}: {e}")
    
    raise HTTPException(status_code=404, detail="Result file not found and recovery failed.")

@app.get("/model-stats")
async def get_model_stats():
    """Get worker-model assignment info"""
    try:
        assigner = WorkerModelAssigner()
        return {
            "status": "success",
            "worker_assignments": assigner.model_assignments,
            "models": assigner.models,
            "info": "Each worker uses a dedicated model. Run start_workers.bat/sh to launch 4 workers."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
async def list_jobs():
    """List all jobs with their status"""
    try:
        jobs = []
        
        # Get all job IDs from status files
        for status_file in Path("uploads").glob("*_status.txt"):
            job_id = status_file.stem.replace("_status", "")
            
            # Read status
            try:
                with open(status_file, 'r') as f:
                    status_data = f.read().strip()
                    if status_data:
                        parts = status_data.split(',')
                        status = parts[0] if parts else "UNKNOWN"
                        progress = int(parts[1]) if len(parts) > 1 else 0
                        total = int(parts[2]) if len(parts) > 2 else 0
                    else:
                        status, progress, total = "UNKNOWN", 0, 0
            except:
                status, progress, total = "ERROR", 0, 0
            
            # Check if result file exists
            result_file = Path(f"uploads/result_{job_id}.xlsx")
            has_result = result_file.exists()
            
            # Get file info
            csv_file = Path(f"uploads/{job_id}.csv")
            original_filename = "unknown.csv"
            upload_time = None
            
            if csv_file.exists():
                upload_time = datetime.fromtimestamp(csv_file.stat().st_mtime).isoformat()
                # Try to get original filename from job_status_db
                if job_id in job_status_db:
                    original_filename = job_status_db[job_id].get('original_filename', 'unknown.csv')
            
            jobs.append({
                "job_id": job_id,
                "status": status,
                "progress": progress,
                "total": total,
                "has_result": has_result,
                "original_filename": original_filename,
                "upload_time": upload_time,
                "download_url": f"/download/{job_id}" if has_result else None
            })
        
        # Sort by upload time (newest first)
        jobs.sort(key=lambda x: x['upload_time'] or '', reverse=True)
        
        return {"jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    try:
        # Revoke the celery task
        celery_app.control.revoke(job_id, terminate=True)
        
        # Update status file
        update_status(job_id, "CANCELLED", 0, 0)
        
        return {"status": "success", "message": f"Job {job_id} cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files"""
    try:
        # Cancel if running
        celery_app.control.revoke(job_id, terminate=True)
        
        # Delete files
        files_to_delete = [
            f"uploads/{job_id}.csv",
            f"uploads/{job_id}_status.txt",
            f"uploads/result_{job_id}.xlsx"
        ]
        
        for file_path in files_to_delete:
            path = Path(file_path)
            if path.exists():
                path.unlink()
        
        # Remove from job_status_db
        if job_id in job_status_db:
            del job_status_db[job_id]
        
        return {"status": "success", "message": f"Job {job_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))