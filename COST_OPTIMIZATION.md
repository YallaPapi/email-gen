# Cost Optimization Settings

## Current Configuration (Optimized for Low Cost)

### Model Selection
- **Model Used**: `gpt-3.5-turbo` 
- **Cost**: $0.0015 per 1K input tokens, $0.002 per 1K output tokens
- **Why**: Cheapest GPT model that still provides high-quality results

### Token Optimization
- **Max Tokens per Step**: 120 (reduced from 150)
- **Total per Email**: 240 tokens max (2 steps × 120)
- **Actual Usage**: ~80-100 tokens per email typical

### Cost Breakdown

#### Per Email Cost
- Step 1 (Base): ~150 input tokens + 80 output tokens
- Step 2 (Rewrite): ~200 input tokens + 80 output tokens
- **Total**: ~350 input + 160 output = 510 tokens
- **Cost**: ~$0.0008 per email

#### Daily Campaign Cost (5,000 emails)
- Total tokens: 5,000 × 510 = 2,550,000 tokens
- **Estimated cost**: $4.00 per day
- **Monthly cost**: ~$120 for 150,000 emails

## Further Cost Reduction Options

### 1. Use GPT-3.5-Turbo Only
✅ **Already implemented** - All workers use gpt-3.5-turbo

### 2. Reduce Token Limits
✅ **Already implemented** - Reduced from 150 to 120 tokens

### 3. Batch Processing
- Process multiple emails in single API calls
- Requires code restructuring
- Could save 20-30% on API calls

### 4. Cache Common Industries
- Store templates for frequently used industries
- Reduces API calls for common cases
- Estimated 10-15% cost reduction

### 5. Single-Step Mode (Emergency)
If costs need to be cut drastically:
- Skip Step 2 (rewrite)
- Use only base generation
- **Cost reduction**: 50%
- **Trade-off**: Less variation

## Current Settings Location

### Files Updated for Cost Optimization:
1. `backend/worker_models.py` - All workers use gpt-3.5-turbo
2. `backend/tasks.py` - Max tokens reduced to 120
3. `.env` - API key configuration

## Monitoring Costs

### OpenAI Dashboard
Monitor actual usage at: https://platform.openai.com/usage

### Daily Limits
The system automatically stops if daily limits are hit:
- Check for "DAILY_LIMIT_HIT" in email results
- Adjust OpenAI account limits if needed

## Quick Changes

### To reduce costs further:
```python
# In backend/tasks.py, change:
max_tokens=120  # Current setting

# To:
max_tokens=80   # More aggressive limit
```

### To switch to single-step mode:
```python
# In backend/tasks.py, comment out Step 2:
# Skip the rewrite step to save 50% on costs
final_email = base_email  # Use base directly
```

## Cost Calculator

| Emails/Day | Token Usage | Daily Cost | Monthly Cost |
|------------|-------------|------------|--------------|
| 1,000      | 510K        | $0.80      | $24          |
| 5,000      | 2.55M       | $4.00      | $120         |
| 10,000     | 5.1M        | $8.00      | $240         |
| 25,000     | 12.75M      | $20.00     | $600         |

## Recommendations

For 5,000 emails/day campaigns:
1. ✅ Use gpt-3.5-turbo (implemented)
2. ✅ Limit tokens to 120 (implemented)
3. ✅ Use rate limiting (implemented)
4. Monitor daily usage in OpenAI dashboard
5. Set spending limits in OpenAI account

Current configuration is optimized for best balance of:
- Low cost ($0.0008 per email)
- High variation (two-step process)
- Good quality (GPT-3.5-Turbo)