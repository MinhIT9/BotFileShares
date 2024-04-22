# api_utlis.py 

import requests, asyncio, aiohttp
from config import USER_ACTIVATIONS_API

# Hàm lấy activation_links từ API
def load_activation_links(api_url):
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to load activation links from API")
        return {}

async def delete_code_from_api(code_id):
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{USER_ACTIVATIONS_API}/{code_id}") as response:
            if response.status == 200:
                print(f"Code {code_id} deleted successfully.")
            else:
                error_text = await response.text()
                print(f"Failed to delete code {code_id}: {error_text}")

# Hàm đồng bộ để lấy activation_links từ API
async def fetch_activation_links():
    async with aiohttp.ClientSession() as session:
        async with session.get(USER_ACTIVATIONS_API) as response:
            if response.status == 200:
                data = await response.json()
                return {item['Code']: {'url': item['Link'], 'duration': item['duration'], 'id': item['id']} for item in data}
            return {}
        
async def update_activation_links():
    return await fetch_activation_links()