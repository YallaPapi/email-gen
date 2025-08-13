# Email Generator Scaling Plan - Multi-Model API Key Rotation

## Project Summary

Based on comprehensive review of the email-gen repository, here's the current system and scaling strategy:

### **Current System Overview**

**What it does**: A scalable email generation system that processes CSV files with lead data and generates personalized cold emails using OpenAI's API.

**Architecture**:
- **FastAPI Backend** (`backend/main.py`) - File upload, job tracking, downloads
- **Celery Task Processing** (`backend/tasks.py`) - Distributed parallel email generation  
- **Redis** - Task queue broker and progress tracking
- **Docker** - Containerized deployment with multiple workers
- **Frontend** - Simple HTML interface for file upload/download

**Current Performance**:
- **Processing Rate**: ~1 email/second (limited by OpenAI rate limits)
- **Daily Capacity**: 10,000 emails/day (OpenAI gpt-3.5-turbo limit)
- **Scalability**: 2 worker containers, horizontally scalable
- **File Size Limit**: 50MB uploads

**Current Limitations**:
- **10,000 requests/day limit** on OpenAI API (currently using gpt-3.5-turbo)
- **1 request/second rate limiting** with global thread locks
- **Single API key** - no rotation/fallback system
- **Partial results handling** when daily limits are hit

## **Scaling Plan: Multi-Model API Key Rotation**

### **Phase 1: Multi-API Key Infrastructure**

#### **1. API Key Pool Management**
- Create a configuration system to manage multiple OpenAI API keys
- Track usage per key with daily counters stored in Redis
- Implement automatic key rotation when limits are approached
- Add key health monitoring and automatic failover

#### **2. Enhanced Rate Limiting**
- Replace global rate limiter with per-key rate limiting
- Dynamic rate adjustment based on API responses (429 errors)
- Intelligent backoff when approaching daily limits
- Per-key request counters with Redis persistence

#### **Technical Changes Required**:
```python
# New KeyManager class in tasks.py
class APIKeyManager:
    def __init__(self):
        self.keys = self.load_keys_from_config()
        self.usage_tracking = {}  # Per-key daily usage
    
    def get_available_key(self):
        # Return key with lowest usage under daily limit
        pass
    
    def track_usage(self, key, model):
        # Increment usage counter in Redis
        pass
```

### **Phase 2: Multi-Model Fallback System**

#### **1. Model Hierarchy**
- **Primary**: `gpt-4o-mini` (higher quality, higher limits)
- **Secondary**: `gpt-3.5-turbo` (backup when primary exhausted)
- **Tertiary**: `gpt-4o` (premium fallback for critical batches)

#### **2. Smart Model Selection**
- Route requests based on current usage across all keys
- Automatically downgrade models as limits approach
- Maintain quality preference while maximizing throughput
- Model-specific rate limiting and usage tracking

#### **Expected Capacity by Model**:
- `gpt-4o-mini`: 10,000+ requests/day per key
- `gpt-3.5-turbo`: 10,000 requests/day per key  
- `gpt-4o`: 5,000 requests/day per key (premium tier)

### **Phase 3: Advanced Orchestration**

#### **1. Usage Tracking Dashboard**
- Real-time monitoring of all API keys and models
- Daily/hourly usage analytics with Redis-based metrics
- Predictive capacity planning based on historical usage
- Alert system for approaching limits

#### **2. Intelligent Job Distribution**
- Split large batches across multiple key/model combinations
- Load balancing based on current capacity
- Priority queuing for urgent vs. bulk processing
- Batch size optimization based on available capacity

## **Technical Implementation Strategy**

### **Key Changes Needed**:

1. **Configuration System**
   ```yaml
   # config/api_keys.yml
   openai_keys:
     - key: "sk-key1..."
       tier: "premium"
       daily_limit: 10000
     - key: "sk-key2..."
       tier: "standard" 
       daily_limit: 10000
   ```

2. **Key Manager Class**
   - Track usage per key/model combination
   - Implement rotation logic with Redis persistence
   - Handle rate limit detection and automatic failover

3. **Enhanced Task System**
   - Modify `process_single_email` to use key manager
   - Add model fallback logic
   - Improved error handling for quota exhaustion

4. **Monitoring Integration**
   - Redis-based usage tracking per key/model
   - Real-time capacity monitoring
   - Historical analytics and reporting

5. **Graceful Degradation**
   - Continue processing with available resources
   - Partial result saving when some keys exhausted
   - Automatic job resumption when limits reset

### **Expected Capacity Increases**:

- **Current**: 10,000 emails/day (1 key, gpt-3.5-turbo)
- **With 3 keys**: 30,000 emails/day  
- **With model mixing**: 40,000+ emails/day (leveraging different model limits)
- **With optimization**: 50,000+ emails/day (intelligent distribution)

## **Implementation Priority**

### **Phase 1 (Immediate) - Multi-Key Rotation**
- **Timeline**: 1-2 days
- **Capacity Increase**: 2-3x (20,000-30,000 emails/day)
- **Changes**: Key management, rotation logic, usage tracking

### **Phase 2 (Short-term) - Model Fallback**
- **Timeline**: 3-5 days  
- **Capacity Increase**: Additional 30-50% (35,000-45,000 emails/day)
- **Changes**: Model hierarchy, smart selection, enhanced error handling

### **Phase 3 (Medium-term) - Advanced Monitoring**
- **Timeline**: 1-2 weeks
- **Capacity Increase**: Optimization gains (50,000+ emails/day)
- **Changes**: Dashboard, analytics, predictive scaling

### **Phase 4 (Long-term) - Enterprise Features**
- **Timeline**: 1 month+
- **Features**: Priority queues, SLA management, advanced analytics

## **Risk Mitigation**

### **Technical Risks**:
- **API Key Management**: Secure storage, rotation without service interruption
- **Rate Limit Coordination**: Accurate tracking across distributed workers
- **Data Consistency**: Ensuring usage counters remain accurate under load

### **Business Risks**:
- **Cost Management**: Monitor spending across multiple API keys
- **Quality Control**: Ensure model fallbacks maintain email quality
- **Compliance**: Handle API terms of service across multiple accounts

## **Success Metrics**

- **Throughput**: Daily email generation capacity
- **Reliability**: Percentage of jobs completed successfully
- **Efficiency**: Cost per email generated across different models
- **Availability**: System uptime during peak processing periods

## **Next Steps**

1. **Confirm Approach**: Review and approve scaling strategy
2. **Acquire Resources**: Obtain additional OpenAI API keys
3. **Begin Implementation**: Start with Phase 1 multi-key rotation
4. **Testing**: Validate with small batches before full deployment
5. **Monitoring**: Establish baseline metrics before scaling

This modular approach allows incremental implementation without disrupting the existing working system, while providing clear capacity increases at each phase.