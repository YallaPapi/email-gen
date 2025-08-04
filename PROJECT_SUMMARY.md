# Scalable Email Generator - Clean Project

## 🎯 Project Overview
A highly scalable email generation system using AI automation to create personalized cold emails. The system generates email sequences (initial + 2 follow-ups) with industry-specific content and nuclear-level cleaning to ensure professional output.

## ✅ Core Features
- **Personalized Email Generation**: Uses OpenAI API with enhanced prompts containing 5 examples each
- **Nuclear Content Cleaning**: Removes subject lines, signatures, and unwanted formatting
- **Scalable Processing**: 4 Celery workers with different GPT models for distributed processing  
- **Real-time Progress Tracking**: Live progress bars and status updates via Redis
- **Multiple File Formats**: Supports CSV and Excel input/output
- **Robust Error Handling**: Auto-retry, rate limiting, and error recovery

## 🏗️ Architecture

### Core Files (Active)
```
├── docker-compose.yml          # Main orchestration
├── backend/
│   ├── tasks.py               # Main email generation logic (ENHANCED PROMPTS)
│   ├── main.py                # FastAPI web server
│   ├── worker_models.py       # Model assignment per worker
│   ├── celeryconfig.py        # Celery configuration
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Container setup
│   └── index.html             # Web interface
└── uploads/                   # Job files and results
```

### Archived Files
```
ARCHIVE/
├── backend_backups/           # Old task file versions
├── test_files/               # All test and debug files
├── documentation/            # ZAD reports and implementation docs
├── results/                  # Generated email results from testing
└── debug_files/              # Unused helper scripts
```

## 🚀 Quick Start

1. **Start the system:**
   ```bash
   docker-compose up -d
   ```

2. **Access the interface:**
   ```
   http://localhost:8000
   ```

3. **Upload a CSV/Excel file** with columns:
   - `first_name`, `organization_name`, `industry` (minimum required)
   - Additional columns will be used for personalization

4. **Choose mode:**
   - **Sequence**: Generates initial + 2 follow-up emails
   - **Single**: Generates one initial email only

## 🎨 Enhanced Prompts
The system uses sophisticated prompts with **5 examples each** for:
- **Initial Email**: Personalized outreach with natural tone
- **Follow-up 1**: Industry-specific challenges and AI solutions  
- **Follow-up 2**: Humorous final attempt with personality

## 🔧 Nuclear Cleaning System
Advanced regex-based cleaning that removes:
- Subject lines (`Subject:` patterns)
- Signatures (`Cheers!`, `Best!`, `[Your Name]`, etc.)  
- Unwanted formatting while preserving email structure

## 🏃‍♂️ Performance
- **4 Workers** with different GPT models for load distribution
- **Rate Limiting**: 0.2s between API calls per worker
- **Auto-retry**: Failed requests retry with exponential backoff
- **Progress Tracking**: Real-time updates via Redis

## 📁 Job History
- Jobs are stored in `uploads/` directory
- Status files track progress: `{job_id}_status.txt`
- Results saved as Excel: `result_{job_id}.xlsx`

## 🔍 Monitoring
- **Flower UI**: http://localhost:5555 (Celery monitoring)
- **Redis**: Port 6379 for progress tracking
- **Logs**: Docker logs show processing details

## 🎯 Key Success Metrics
- ✅ **Zero subject lines or signatures** in generated emails
- ✅ **Highly personalized content** using prospect data
- ✅ **Industry-specific insights** in follow-up emails
- ✅ **Creative humor** in final follow-ups
- ✅ **Scalable processing** for large datasets

---

*This project has been cleaned and optimized for production use. All test files, backups, and documentation have been archived for reference.*