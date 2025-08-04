#!/usr/bin/env python3
"""
Comprehensive test of email sequence generation across multiple industries
"""
import pandas as pd
import requests
import time
import os

def comprehensive_test():
    test_file = "comprehensive_test.csv"
    
    print("🚀 COMPREHENSIVE EMAIL SEQUENCE TEST")
    print("=" * 50)
    print(f"📄 Testing with: {test_file}")
    
    # Upload file
    with open(test_file, 'rb') as f:
        files = {'file': f}
        data = {'mode': 'sequence'}
        response = requests.post('http://localhost:8000/upload', files=files, data=data)
    
    if response.status_code != 200:
        print(f"❌ UPLOAD FAILED: {response.text}")
        return False
    
    job_id = response.json()['job_id']
    print(f"✅ Upload successful! Job ID: {job_id}")
    
    # Monitor progress
    print("⏳ Monitoring progress...")
    start_time = time.time()
    
    while time.time() - start_time < 120:  # 2 minute timeout
        response = requests.get(f'http://localhost:8000/status/{job_id}')
        if response.status_code == 200:
            status_data = response.json()
            status = status_data.get('status', 'UNKNOWN')
            progress = status_data.get('progress', 0)
            total = status_data.get('total', 0)
            
            print(f"   Status: {status}, Progress: {progress}/{total}")
            
            if status == "SUCCESS":
                print("✅ Processing completed!")
                break
            elif status.startswith("FAILURE") or status.startswith("ERROR"):
                print(f"❌ PROCESSING FAILED: {status}")
                return False
        
        time.sleep(3)
    else:
        print("❌ TIMEOUT - Processing took too long")
        return False
    
    # Download and analyze
    response = requests.get(f'http://localhost:8000/download/{job_id}')
    if response.status_code != 200:
        print(f"❌ DOWNLOAD FAILED: {response.status_code}")
        return False
    
    result_file = f"test_result_{job_id}.xlsx"
    with open(result_file, 'wb') as f:
        f.write(response.content)
    
    # Comprehensive analysis
    df = pd.read_excel(result_file)
    print(f"\n📊 ANALYSIS RESULTS")
    print("=" * 30)
    
    # Check all required columns exist
    required_cols = ['initial_email', 'followup_1', 'followup_2']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ MISSING COLUMNS: {missing_cols}")
        return False
    print(f"✅ All required columns present: {required_cols}")
    
    # Check all emails generated
    total_contacts = len(df)
    total_emails_expected = total_contacts * 3
    
    email_count = 0
    for _, row in df.iterrows():
        for col in required_cols:
            if pd.notna(row[col]) and str(row[col]).strip() and not str(row[col]).startswith('ERROR'):
                email_count += 1
    
    print(f"✅ Email Generation: {email_count}/{total_emails_expected} emails created")
    
    if email_count != total_emails_expected:
        print(f"❌ INCOMPLETE GENERATION - Expected {total_emails_expected}, got {email_count}")
        return False
    
    # Template detection
    template_phrases = [
        "Hey [name], hope you're good. Just wanted to shoot you this quick email",
        "with a little more info about how we would be able to help"
    ]
    
    template_found = False
    for phrase in template_phrases:
        count = 0
        for _, row in df.iterrows():
            for col in required_cols:
                if pd.notna(row[col]) and phrase in str(row[col]):
                    count += 1
        if count > 0:
            print(f"❌ TEMPLATE DETECTED: '{phrase}' found {count} times")
            template_found = True
    
    if not template_found:
        print("✅ NO TEMPLATES: All emails are personalized")
    
    # Industry-specific content check
    industry_keywords = {
        'Software': ['automated testing', 'code review', 'deployment', 'bug detection'],
        'Legal': ['document review', 'client intake', 'legal research', 'contract'],
        'Healthcare': ['appointment scheduling', 'patient record', 'diagnostic'],
        'Marketing': ['campaign optimization', 'content generation', 'lead scoring'],
        'Finance': ['fraud detection', 'loan processing', 'compliance']
    }
    
    industry_targeting = True
    for _, row in df.iterrows():
        industry = row.get('industry', '')
        if industry in industry_keywords:
            keywords = industry_keywords[industry]
            followup1 = str(row.get('followup_1', '')).lower()
            
            if not any(keyword.lower() in followup1 for keyword in keywords):
                print(f"❌ INDUSTRY TARGETING: {row['first_name']} ({industry}) missing relevant keywords")
                industry_targeting = False
    
    if industry_targeting:
        print("✅ INDUSTRY TARGETING: All emails contain relevant industry benefits")
    
    # Uniqueness check
    followup1_starts = []
    for _, row in df.iterrows():
        if pd.notna(row['followup_1']):
            start = str(row['followup_1'])[:50]
            followup1_starts.append(start)
    
    unique_starts = len(set(followup1_starts))
    total_starts = len(followup1_starts)
    
    print(f"✅ UNIQUENESS: {unique_starts}/{total_starts} unique follow-up email starts")
    
    # Show sample per industry
    print(f"\n📧 SAMPLE EMAILS BY INDUSTRY")
    print("=" * 40)
    
    for _, row in df.iterrows():
        print(f"\n👤 {row['first_name']} at {row['organization_name']} ({row['industry']}):")
        print(f"   INITIAL: {str(row['initial_email'])[:80]}...")
        print(f"   FOLLOW-UP 1: {str(row['followup_1'])[:80]}...")
        print(f"   FOLLOW-UP 2: {str(row['followup_2'])[:80]}...")
    
    # Cleanup
    os.remove(result_file)
    print(f"\n🧹 Cleaned up {result_file}")
    
    # Final verdict
    all_tests_passed = (
        email_count == total_emails_expected and
        not template_found and
        industry_targeting and
        unique_starts == total_starts
    )
    
    if all_tests_passed:
        print(f"\n🎉 ALL TESTS PASSED - SYSTEM WORKING FLAWLESSLY")
        print(f"   ✅ {total_contacts} contacts processed")
        print(f"   ✅ {total_emails_expected} personalized emails generated")
        print(f"   ✅ 0 template phrases detected")
        print(f"   ✅ 100% industry-specific targeting")
        print(f"   ✅ 100% email uniqueness")
        return True
    else:
        print(f"\n❌ TESTS FAILED - ISSUES DETECTED")
        return False

if __name__ == "__main__":
    success = comprehensive_test()
    exit(0 if success else 1)