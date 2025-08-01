# Email Generator Implementation Plan

## Current State Audit

### Critical Issues Found:
1. **Backend (main.py)**:
   - No file validation (accepts any file type/size)
   - Synchronous file operations in async endpoints
   - No proper error handling
   - Security vulnerability: files saved with user-provided filenames
   - No cleanup of old files

2. **Backend (tasks.py)**:
   - Missing email generation prompts (shows "...")
   - No retry logic for OpenAI API failures
   - No rate limiting
   - Blocking sleep in Celery task

3. **Frontend**:
   - Completely empty - just has title
   - No file upload form
   - No status display
   - No download functionality

4. **Docker**:
   - Setup looks correct but needs testing

## Implementation Plan

### Phase 1: Fix Critical Backend Issues (PRIORITY)
1. Add proper email generation prompt
2. Add file validation (CSV/XLSX only, <10MB)
3. Add async file operations with aiofiles
4. Sanitize filenames using UUID
5. Add basic error handling

### Phase 2: Create Minimal Frontend
1. Add file upload form
2. Add status polling
3. Add download button
4. Basic styling for usability

### Phase 3: Testing & Deployment
1. Test with real CSV file
2. Verify Docker setup works
3. Add basic logging

## Execution Order:
1. Fix tasks.py prompts ✓
2. Fix main.py validation ✓  
3. Create working frontend ✓
4. Test end-to-end ✓
5. Docker deployment ✓