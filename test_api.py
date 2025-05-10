import requests
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

TINKOFF_TOKEN = os.getenv('TINKOFF_SANDBOX_TOKEN')

BASE_URLS = [
    'https://api-invest.tinkoff.ru/openapi/sandbox/',
    'https://invest-public-api.tinkoff.ru/openapi/sandbox/'
]

def test_endpoint(url, endpoint):
    try:
        response = requests.get(
            f"{url}{endpoint}",
            headers={"Authorization": f"Bearer {TINKOFF_TOKEN}"}
        )
        response.raise_for_status()
        logging.info(f"Endpoint {endpoint} at {url} status: {response.status_code}")
        logging.info(f"Response: {response.text}")
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error for {endpoint} at {url}: {str(e)}, response: {response.text}")
        return None
    except Exception as e:
        logging.error(f"Error for {endpoint} at {url}: {str(e)}")
        return None

def test_api():
    endpoints = ['user/accounts', 'market/currencies', 'market/stocks', 'sandbox/register']
    for url in BASE_URLS:
        logging.info(f"Testing URL: {url}")
        for endpoint in endpoints:
            result = test_endpoint(url, endpoint)
            if result:
                logging.info(f"Success for {endpoint}: {result}")

if __name__ == "__main__":
    if not TINKOFF_TOKEN:
        logging.error("TINKOFF_SANDBOX_TOKEN is not set in .env")
    else:
        test_api()