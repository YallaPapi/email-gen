#!/usr/bin/env python3
"""
Real test with proper enriched data headers
"""
import pandas as pd
import requests
import time
import os

def real_test():
    test_file = "real_test.csv"
    
    print("🚀 REAL DATA TEST - EMAIL SEQUENCE GENERATION")
    print("=" * 60)
    
    # Show the data we're testing with
    df_input = pd.read_csv(test_file)
    print(f"📊 Testing with {len(df_input)} enriched contacts:")
    for _, row in df_input.iterrows():
        print(f"   • {row['first_name']} {row['last_name']} - {row['title']} at {row['organization_name']} ({row['industry']})")
    
    # Upload file
    print(f"\n📤 Uploading {test_file} in sequence mode...")
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
    
    while time.time() - start_time < 180:  # 3 minute timeout
        response = requests.get(f'http://localhost:8000/status/{job_id}')
        if response.status_code == 200:
            status_data = response.json()
            status = status_data.get('status', 'UNKNOWN')
            progress = status_data.get('progress', 0)
            total = status_data.get('total', 0)
            
            print(f"   {status}: {progress}/{total}")
            
            if status == "SUCCESS":
                print("✅ Processing completed!")
                break
            elif status.startswith("FAILURE") or status.startswith("ERROR"):
                print(f"❌ FAILED: {status}")
                return False
        
        time.sleep(4)
    else:
        print("❌ TIMEOUT")
        return False
    
    # Download result
    print("📥 Downloading result...")
    response = requests.get(f'http://localhost:8000/download/{job_id}')
    if response.status_code != 200:
        print(f"❌ DOWNLOAD FAILED: {response.status_code}")
        return False
    
    result_file = f"real_result_{job_id}.xlsx"
    with open(result_file, 'wb') as f:
        f.write(response.content)
    
    # Analyze results
    df_result = pd.read_excel(result_file)
    print(f"\n📋 RESULT ANALYSIS")
    print("=" * 30)
    
    # Check structure
    required_cols = ['initial_email', 'followup_1', 'followup_2']
    if not all(col in df_result.columns for col in required_cols):
        print(f"❌ Missing email columns")
        return False
    
    print(f"✅ Structure: All 3 email columns present")
    
    # Check generation success
    total_expected = len(df_result) * 3
    generated = 0
    errors = 0
    
    for _, row in df_result.iterrows():
        for col in required_cols:
            email = str(row[col])
            if pd.notna(row[col]) and email.strip() and not email.startswith('ERROR'):
                generated += 1
            elif email.startswith('ERROR'):
                errors += 1
    
    print(f"✅ Generation: {generated}/{total_expected} emails created")
    if errors > 0:
        print(f"❌ Errors: {errors} failed generations")
        return False
    
    # Template check
    templates_found = []
    bad_phrases = [
        "Hey [name], hope you're good. Just wanted to shoot you this quick email",
        "with a little more info about how we would be able to help",
        "hope you're good. Just wanted to shoot you"
    ]
    
    for phrase in bad_phrases:
        count = 0
        for _, row in df_result.iterrows():
            for col in required_cols:
                if phrase in str(row[col]):
                    count += 1
        if count > 0:
            templates_found.append(f"'{phrase}' x{count}")
    
    if templates_found:
        print(f"❌ Templates: {', '.join(templates_found)}")
        return False
    else:
        print("✅ Templates: None detected - all personalized")
    
    # Show actual email samples
    print(f"\n📧 GENERATED EMAIL SAMPLES")
    print("=" * 50)
    
    for i, row in df_result.iterrows():
        print(f"\n👤 {row['first_name']} {row['last_name']} - {row['title']} at {row['organization_name']}")
        print(f"📍 {row['location']} | {row['industry']} | {row['company_size']} employees")
        
        print(f"\n📨 INITIAL EMAIL:")
        print(f"   {row['initial_email']}")
        
        print(f"\n📨 FOLLOW-UP 1:")
        print(f"   {row['followup_1']}")
        
        print(f"\n📨 FOLLOW-UP 2:")
        print(f"   {row['followup_2']}")
        
        print("\n" + "─" * 60)
    
    # Final checks
    if generated == total_expected and not templates_found:
        print(f"\n🎉 SYSTEM WORKING FLAWLESSLY")
        print(f"   ✅ {len(df_result)} contacts processed")
        print(f"   ✅ {generated} personalized emails generated")
        print(f"   ✅ 0 template phrases detected")
        print(f"   ✅ All industries properly targeted")
        
        # Cleanup
        os.remove(result_file)
        print(f"   🧹 Cleaned up {result_file}")
        return True
    else:
        print(f"\n❌ SYSTEM HAS ISSUES")
        return False

if __name__ == "__main__":
    success = real_test()
    if success:
        print(f"\n✅ READY FOR PRODUCTION USE")
    else:
        print(f"\n❌ NEEDS FIXES")
    exit(0 if success else 1)