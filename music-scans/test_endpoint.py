#!/usr/bin/env python3
import requests
import json

# Test the /api/lessons endpoint
try:
    response = requests.get('http://localhost:5000/api/lessons')
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Text: {response.text}")
    print(f"Response JSON: {response.json()}")
    print(f"Number of lessons: {len(response.json())}")
except Exception as e:
    print(f"Error: {e}")
