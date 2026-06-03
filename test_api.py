#!/usr/bin/env python3
import requests
import json

# 测试健康检查
print("Testing health endpoint...")
try:
    r = requests.get("<SIGNED_URL_REMOVED>")
    print(f"Health check: {r.status_code} {r.text}")
except Exception as e:
    print(f"Health check failed: {e}")

# 测试股票API
print("\nTesting stocks API...")
try:
    r = requests.post("<SIGNED_URL_REMOVED>",
                      json={"codes": ["sh600519", "sz000001"]},
                      timeout=10)
    print(f"Stocks API: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Stocks API failed: {e}")

print("\nTest completed.")
