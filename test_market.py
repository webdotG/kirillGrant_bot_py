import requests
import os
from dotenv import load_dotenv

load_dotenv()
TINKOFF_TOKEN = os.getenv('TINKOFF_SANDBOX_TOKEN')
BASE_URL = 'https://sandbox-invest-public-api.tinkoff.ru:443'

response = requests.get(
    f"{BASE_URL}/market/currencies",
    headers={"Authorization": f"Bearer {TINKOFF_TOKEN}"}
)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")