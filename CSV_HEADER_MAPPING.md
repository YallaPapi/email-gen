# CSV Header Mapping

## Headers the System Uses

### Required Fields (Must Have)
| CSV Header | System Variable | Usage | Status in Test Sheet |
|------------|----------------|--------|----------------------|
| `first_name` | first_name | Recipient's name in greeting | ✅ Present |
| `organization_name` | company_name | Company reference in email | ✅ Present |
| `industry` | industry | Determines AI solutions | ✅ Present |

### Optional Fields (Enhances Quality)
| CSV Header | System Variable | Usage | Status in Test Sheet |
|------------|----------------|--------|----------------------|
| `organization_short_description` | org_description | Additional context for personalization | ✅ Present |

## All Headers in Test Sheet CSV

### Used by System (4 headers)
- ✅ `first_name` - Used for greeting
- ✅ `organization_name` - Used for company reference
- ✅ `industry` - Used for AI solution selection
- ✅ `organization_short_description` - Used for additional context

### Not Used by System (19 headers)
- ❌ `title` - Job title (could be useful for personalization)
- ❌ `email` - Email address (for sending, not generation)
- ❌ `country` - Location info
- ❌ `estimated_num_employees` - Company size
- ❌ `organization_annual_revenue` - Revenue data
- ❌ `name` - Full name (system uses first_name)
- ❌ `organization_founded_year` - Company age
- ❌ `city` - Location detail
- ❌ `phone_numbers/0/dialer_flags` - Phone metadata
- ❌ `phone_numbers/0/dnc_status` - Do not call status
- ❌ `phone_numbers/0/position` - Phone position
- ❌ `phone_numbers/0/raw_number` - Raw phone
- ❌ `phone_numbers/0/sanitized_number` - Clean phone
- ❌ `phone_numbers/0/source_name` - Phone source
- ❌ `phone_numbers/0/status` - Phone status
- ❌ `phone_numbers/0/third_party_vendor_name` - Vendor info
- ❌ `phone_numbers/0/type` - Phone type
- ❌ `organization_phone` - Company phone
- ❌ `linkedin_url` - LinkedIn profile

## Sample Data from Test Sheet

| Row | first_name | organization_name | industry | organization_short_description |
|-----|------------|------------------|----------|--------------------------------|
| 1 | Dan | Chick-fil-A Corporate Support Center | restaurants | Chick-fil-A is a Georgia-based company that owns and operates a chain of restaurants... |
| 2 | La | La Casa Global | real estate | A family-run real estate and property management company... |
| 3 | Steve | Vertical Runner Corp. | sporting goods | Vertical Runner is a run specialty store... |

## Mapping Summary

**✅ READY TO RUN**: The test sheet CSV has all required headers properly named:
- `first_name` ✅
- `organization_name` ✅
- `industry` ✅
- `organization_short_description` ✅ (optional but present)

No code changes needed - the CSV headers match exactly what the system expects!