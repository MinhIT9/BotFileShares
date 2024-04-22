# api_utlis.py 

import requests, asyncio, aiohttp, datetime
from config import USER_ACTIVATIONS_API, USERS_ACCESS_API, Config

# Gán biến
config_instance = Config()
users_access = config_instance.users_access 

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




async def get_all_users_access():
    async with aiohttp.ClientSession() as session:
        async with session.get(USERS_ACCESS_API) as response:
            if response.status == 200:
                return await response.json()
            else:
                print("Failed to load users access data from API")
                return None
            
async def get_or_create_users_access_object():
    all_users_access = await get_all_users_access()
    if all_users_access is None:
        return None
    
    # Tìm đối tượng users_access hiện có không quá 1000 người dùng
    for access_object in all_users_access:
        if len(access_object["users_access"]) < 1000:
            return access_object
    
    # Nếu không tìm thấy, tạo mới
    new_access_object = {"users_access": {}, "id": str(len(all_users_access) + 1)}
    await create_new_users_access_object(new_access_object)
    return new_access_object

async def create_new_users_access_object(access_object):
    async with aiohttp.ClientSession() as session:
        async with session.post(USERS_ACCESS_API, json=access_object) as response:
            if response.status in [200, 201]:
                print(f"New users access object created with ID: {access_object['id']}")
            else:
                print(f"Failed to create new users access object")
                
async def update_users_access(user_id, expiry_time):
    access_object = await get_or_create_users_access_object()
    if access_object is None:
        print("Failed to get or create users access object")
        return
    
    # Cập nhật users_access với người dùng mới
    access_object["users_access"][str(user_id)] = expiry_time.isoformat()
    
    # Gửi cập nhật lên mockapi
    await save_single_user_access_to_api(access_object)
            
async def save_single_user_access_to_api(access_object):
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{USERS_ACCESS_API}/{access_object['id']}", json=access_object) as response:
            if response.status in [200, 201]:
                print(f"Users access object with ID {access_object['id']} updated")
            else:
                print(f"Failed to update users access object with ID {access_object['id']}")
                
async def load_users_access_from_api():
    async with aiohttp.ClientSession() as session:
        async with session.get(USERS_ACCESS_API) as response:
            if response.status == 200:
                data = await response.json()
                for entry in data:
                    user_id = int(entry['user_id'])  # Đảm bảo chuyển user_id trở lại thành số
                    expiry_time = datetime.datetime.fromisoformat(entry['expiry_time'])
                    users_access[user_id] = expiry_time
            else:
                print("Failed to load users access data from API")
