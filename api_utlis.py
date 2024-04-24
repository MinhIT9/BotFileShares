# api_utlis.py 

import requests, asyncio, aiohttp, datetime
from config import USER_ACTIVATIONS_API, USERS_ACCESS_API, Config, USER_MSG_ID_API

# Gán biến
config_instance = Config()
users_access = config_instance.users_access 


async def save_msg_id_mapping_to_api(custom_msg_id, telegram_msg_id):
    async with aiohttp.ClientSession() as session:
        # Lấy thông tin hiện tại từ API
        async with session.get(USER_MSG_ID_API) as get_response:
            if get_response.status == 200:
                current_data = await get_response.json()
                # Tìm object cần cập nhật
                for item in current_data:
                    if 'msg_id_mapping' in item:
                        # Cập nhật msg_id_mapping với UUID và Telegram message ID mới
                        item['msg_id_mapping'][custom_msg_id] = telegram_msg_id
                        # PUT cập nhật trở lại API
                        async with session.put(f"{USER_MSG_ID_API}/{item['id']}", json=item) as put_response:
                            if put_response.status in [200, 201]:
                                print("Message ID mapping updated successfully.")
                                return
                print("Failed to find msg_id_mapping in any item.")
            else:
                print("Failed to fetch current data from API.")

async def load_msg_id_mapping_from_api():
    async with aiohttp.ClientSession() as session:
        async with session.get(USER_MSG_ID_API) as response:
            if response.status == 200:
                accounts_data = await response.json()
                msg_id_mappings = {}
                for account in accounts_data:
                    account_id = account['id']
                    for uuid, msg_id in account.get('msg_id_mapping', {}).items():
                        # Bảo đảm rằng các UUID không bị trùng lặp giữa các tài khoản
                        if uuid in msg_id_mappings:
                            print(f"Duplicate UUID found: {uuid}")
                        else:
                            msg_id_mappings[uuid] = msg_id
                return msg_id_mappings
            else:
                print("Failed to load message ID mappings from API.")
                return {}





async def get_or_create_users_access_object():
    all_users_access = await get_all_users_access()
    if all_users_access is None:
        return None

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
                return {
                    item['Code']: {
                        'url': item['Link'],
                        'backup_url': item.get('LinkBackup'),  # Lấy thêm backup link
                        'duration': item['duration'],
                        'id': item['id']
                    }
                    for item in data
                }
            else:
                print(f"Failed to load activation links from API, status code {response.status}")
                return {}
        
async def update_activation_links():
    return await fetch_activation_links()




async def get_all_users_access():
    async with aiohttp.ClientSession() as session:
        async with session.get(USERS_ACCESS_API) as response:
            if response.status == 200:
                return await response.json()
            print("Failed to load users access data from API")
            return None

async def get_or_create_users_access_object():
    all_users_access = await get_all_users_access()
    if not all_users_access:
        return None
    
    for access_object in all_users_access:
        if len(access_object["users_access"]) < 100:
            return access_object

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
    if not access_object:
        print("Failed to get or create users access object")
        return
    
    access_object["users_access"][str(user_id)] = expiry_time.isoformat()
    await save_single_user_access_to_api(access_object)

async def save_single_user_access_to_api(access_object):
    # Hàm này chỉ nhận một đối số là access_object
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{USERS_ACCESS_API}/{access_object['id']}", json=access_object) as response:
            if response.status in [200, 201]:
                print(f"Users access object with ID {access_object['id']} updated")
            else:
                print(f"Failed to update users access object with ID {access_object['id']}")
                
async def delete_user_from_access(user_id):
    # Lấy toàn bộ dữ liệu users_access
    all_users_access = await get_all_users_access()
    if all_users_access is None:
        print("Cannot fetch users access data.")
        return

    # Tìm đối tượng chứa user_id cần xóa
    access_object_to_update = None
    for access_object in all_users_access:
        if str(user_id) in access_object["users_access"]:
            access_object_to_update = access_object
            # Xóa user_id khỏi dictionary
            access_object["users_access"].pop(str(user_id), None)
            break

    # Nếu không tìm thấy đối tượng chứa user_id, không làm gì cả
    if not access_object_to_update:
        print(f"User {user_id} not found in any access object.")
        return

    # Cập nhật lại đối tượng đã sửa trên API
    async with aiohttp.ClientSession() as session:
        async with session.put(f"{USERS_ACCESS_API}/{access_object_to_update['id']}", json=access_object_to_update) as response:
            if response.status in [200, 201]:
                print(f"User {user_id} has been removed from users access data.")
            else:
                error_text = await response.text()
                print(f"Failed to update users access data: {response.status} {error_text}")

async def remove_expired_users_access():
    current_time = datetime.datetime.now()
    all_users_access = await get_all_users_access()
    for access_object in all_users_access:
        expired_user_ids = [user_id for user_id, expiry_str in access_object['users_access'].items()
                            if datetime.datetime.fromisoformat(expiry_str) < current_time]
        for user_id in expired_user_ids:
            access_object['users_access'].pop(user_id, None)
            print(f"Removing expired access for user: {user_id}")
            # Xóa người dùng khỏi API ở đây

        # Cập nhật lại access_object nếu có sự thay đổi
        if expired_user_ids:
            await save_single_user_access_to_api(access_object)

async def schedule_remove_expired_users_access(interval=10):
    while True:
        await remove_expired_users_access()
        await asyncio.sleep(interval)  # Đợi interval giây trước khi kiểm tra lại
                
async def load_users_access_from_api():
    async with aiohttp.ClientSession() as session:
        async with session.get(USERS_ACCESS_API) as response:
            if response.status == 200:
                data = await response.json()
                for access_object in data:
                    if "users_access" in access_object:
                        for user_id, expiry_time_str in access_object["users_access"].items():
                            # Sử dụng phương thức `int()` để chuyển đổi user_id thành số
                            config_instance.users_access[int(user_id)] = datetime.datetime.fromisoformat(expiry_time_str)
                return config_instance.users_access  # Trả về giá trị đã cập nhật
            else:
                print("Failed to load users access data from API")
                return {}  # Trả về dictionary rỗng nếu có lỗi