import requests
import os
from dotenv import load_dotenv

load_dotenv()
TINKOFF_TOKEN = os.getenv('TINKOFF_SANDBOX_TOKEN')
BASE_URL = 'https://sandbox-invest-public-api.tinkoff.ru:443'

def get_sandbox_accounts():
    try:
        response = requests.get(
            f"{BASE_URL}/user/accounts",
            headers={"Authorization": f"Bearer {TINKOFF_TOKEN}"}
        )
        response.raise_for_status()
        print(f"get_sandbox_accounts status: {response.status_code}")
        print(f"get_sandbox_accounts response: {response.text}")
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error in get_sandbox_accounts: {str(e)}, response: {response.text}")
        return None
    except Exception as e:
        print(f"Error in get_sandbox_accounts: {str(e)}")
        return None

print(get_sandbox_accounts())