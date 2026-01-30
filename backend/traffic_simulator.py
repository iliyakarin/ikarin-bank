import json
import uuid
import time
import os
import requests
import random
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL")
TPS = int(os.getenv("TPS", 5))
DURATION = int(os.getenv("DURATION", 60))

CATEGORIES = ["Food", "Transport", "Utilities", "Entertainment", "Shopping"]
MERCHANTS = ["Amazon", "Uber", "Starbucks", "Netflix", "Shell", "Walmart"]

def run_simulator():
    print(f"🚀 Starting traffic simulator at {TPS} TPS for {DURATION} seconds...")
    print(f"🔗 Target API: {API_URL}")
    
    start_time = time.time()
    count = 0
    
    while time.time() - start_time < DURATION:
        payload = {
            "account_id": 1,
            "amount": round(random.uniform(5.0, 500.0), 2),
            "category": random.choice(CATEGORIES),
            "merchant": random.choice(MERCHANTS)
        }
        
        try:
            response = requests.post(f"{API_URL}/transfer", json=payload)
            if response.status_code == 200:
                count += 1
                if count % 10 == 0:
                    print(f"✅ Sent {count} transactions...")
            else:
                print(f"❌ Failed to send transaction: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
            
        time.sleep(1.0 / TPS)

    print(f"🏁 Simulation finished. Sent total {count} transactions.")

if __name__ == "__main__":
    run_simulator()
