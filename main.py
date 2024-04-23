# main.py

from datetime import timedelta
import datetime, random, asyncio, threading, aiohttp, re
from config import Config  # Import class Config
from telethon import events, Button
from api_utlis import delete_code_from_api, fetch_activation_links, save_single_user_access_to_api, load_users_access_from_api, get_or_create_users_access_object
from config import (your_bot_username, channel_id, pending_activations, 
                    user_link_map, distributed_links, LINK_DURATION,
                    client, bot_token, USER_ACTIVATIONS_API)

# Gán biến mới cho users_access, activation_links 
config_instance = Config()
users_access = config_instance.users_access 
activation_links = config_instance.activation_links

# Đây là hàm kiểm tra các kích hoạt đang chờ và nằm ở cấp độ module
def check_pending_activations():
    current_time = datetime.datetime.now()
    expired_users = []
    for user, expiry in pending_activations.items():
        if expiry < current_time:
            expired_users.append(user)
            code = user_link_map.get(user)
            if code:
                # Trả mã về pool nếu hết hạn
                activation_links[code] = distributed_links[code]
                user_link_map.pop(user, None)

    for user in expired_users:
        pending_activations.pop(user, None)
        distributed_links.pop(user, None)

    if expired_users:
        print(f"Các link kích hoạt cho {expired_users} đã hết hạn và giờ đây đã sẵn sàng trở lại.")

async def provide_new_activation_link(event, current_time):
    available_codes = [code for code in activation_links if code not in user_link_map.values()]
    if available_codes:
        random_code = random.choice(available_codes)
        link = activation_links[random_code]['url']
        user_link_map[event.sender_id] = random_code
        pending_activations[event.sender_id] = current_time + LINK_DURATION
        await event.respond(f"Đây là link kích hoạt mới của bạn: {link}", buttons=[Button.url("Kích hoạt", link)], parse_mode='html')
    else:
        await event.respond("Hiện tại không có mã kích hoạt nào khả dụng. Vui lòng thử lại sau.")

        
        
# Xác định regex cho lệnh thêm code
@client.on(events.NewMessage(pattern=r'/newcodettgs ([\s\S]+)'))
async def add_new_code(event):
    codes_data = event.pattern_match.group(1)
    codes_lines = codes_data.strip().split('\n')
    
    async with aiohttp.ClientSession() as session:
        for line in codes_lines:
            parts = line.strip().split()
            if len(parts) == 3:
                payload = {'Code': parts[0], 'Link': parts[1], 'duration': int(parts[2])}
                try:
                    async with session.post(USER_ACTIVATIONS_API, json=payload) as response:
                        if response.status == 201:
                            await event.respond(f"Thêm mã thành công: {payload['Code']}")
                        else:
                            error_message = await response.text()
                            await event.respond(f"Không thể thêm mã {payload['Code']}: {error_message}")
                except aiohttp.ClientError as e:
                    await event.respond(f"Lỗi kết nối API: {str(e)}")
                
@client.on(events.NewMessage(pattern='/updatecode'))
async def handle_update_code_command(event):
    print("Đã nhận yêu cầu cập nhật mã.")
    try:
        new_activation_links = await fetch_activation_links()
        if new_activation_links:
            activation_links = new_activation_links
            await event.respond("Cập nhật mã kích hoạt thành công!")
            print(f"Mã kích hoạt được cập nhật tại {datetime.datetime.now()}.")
        else:
            await event.respond("Không thể cập nhật mã kích hoạt từ API.")
    except Exception as e:
        await event.respond(f"Lỗi khi cập nhật mã: {str(e)}")
        print(f"Lỗi cập nhật mã kích hoạt: {e}")
          
@client.on(events.NewMessage(pattern='/checkcode'))
async def check_code_availability(event):
    global activation_links  # Khai báo sử dụng biến toàn cục
    # Đếm số lượng mã theo từng thời hạn sử dụng
    duration_counts = {}
    for code_info in activation_links.values():  # Không cần gán lại biến activation_links ở đây
        duration = code_info['duration']
        if duration in duration_counts:
            duration_counts[duration] += 1
        else:
            duration_counts[duration] = 1
    
    # Tạo và gửi thông báo về số lượng mã theo từng thời hạn
    response_message = "<b>Tình trạng mã kích hoạt VIP hiện tại:</b>\n"
    for duration, count in sorted(duration_counts.items()):
        response_message += f"Code VIP: <b>{duration} ngày</b> - còn lại: <b>{count} mã</b> \n"
    
    # Thêm thông báo hướng dẫn sử dụng /kichhoat
    response_message += "\n Mã hoàn toàn ngẫu nhiên,\nnên chúc các bạn may mắn nhé! \n \n 👍 Sử dụng <b>/kichhoat</b> để lấy mã kích hoạt VIP.\n \n Bản quyền thuộc về @BotShareFilesTTG"

    # Kiểm tra nếu có mã khả dụng để gửi phản hồi
    if duration_counts:
        await event.respond(response_message, parse_mode='html')
    else:
        await event.respond("Hiện không có mã kích hoạt nào khả dụng.")

@client.on(events.NewMessage(pattern=r'/kichhoat'))
async def request_activation_link(event):
    user_id = event.sender_id
    current_time = datetime.datetime.now()

    # Kiểm tra xem người dùng đã nhận link chưa và link đó có còn hiệu lực không
    if user_id in pending_activations:
        # Kiểm tra nếu người dùng đã là VIP và gửi thông báo hạn sử dụng
        if user_id in users_access and current_time < users_access[user_id]:
            expiry_str = users_access[user_id].strftime('%H:%M %d-%m-%Y')
            await event.respond(f"Bạn đã là VIP và hạn sử dụng đến: {expiry_str}. Sử dụng /kichhoat để tăng thời gian sử dụng.")
        else:
            # Link đã hết hạn, cung cấp link mới
            await provide_new_activation_link(event, current_time)
    else:
        # Người dùng chưa có link, cung cấp link mới
        await provide_new_activation_link(event, current_time)
        
@client.on(events.NewMessage(pattern=r'/code (\d+)'))
async def activate_code(event):
    user_id = event.sender_id
    code_entered = event.pattern_match.group(1).strip()
    current_time = datetime.datetime.now()
    
     # Đảm bảo rằng activation_links là một dictionary toàn cục
    global activation_links
    global users_access

    if code_entered in activation_links and (code_entered not in distributed_links or distributed_links.get(code_entered) == user_id):
        code_info = activation_links[code_entered]
        duration = timedelta(days=code_info["duration"])
        # Nếu không tìm thấy user_id trong users_access, sử dụng current_time làm giá trị mặc định
        expiry_time = users_access.get(user_id, current_time)
        new_expiry_time = expiry_time + duration
        
        # Cập nhật users_access trong instance và pool
        users_access[user_id] = new_expiry_time
        distributed_links[code_entered] = user_id

        # Lấy hoặc tạo đối tượng users_access để lưu trữ thông tin
        access_object = await get_or_create_users_access_object()
        if access_object is None:
            await event.respond("Không thể cập nhật hoặc tạo mới thông tin truy cập.")
            return

        access_object["users_access"][str(user_id)] = new_expiry_time.isoformat()
        # Lưu trữ thông tin sau khi kích hoạt thành công
        await save_single_user_access_to_api(access_object)  # Sửa đổi tại đây

        # Xóa mã khỏi API và pool
        del activation_links[code_entered]
        await delete_code_from_api(code_info['id'])

        # Sử dụng new_expiry_time để tạo thông báo
        expiry_str = new_expiry_time.strftime('%H:%M %d-%m-%Y')
        await event.respond(f"Bạn đã kích hoạt thành công VIP. Hạn sử dụng đến: {expiry_str}.")
    else:
        await event.respond("Mã kích hoạt không hợp lệ hoặc đã được sử dụng. Vui lòng nhập đúng cú pháp: <b>/code 12345</b>.", parse_mode='html')

@client.on(events.NewMessage(pattern='/start'))
async def send_welcome(event):
    check_pending_activations()
    # Kiểm tra payload từ link /start để xác định xem có cần forward tin nhắn từ channel không
    if event.message.message.startswith('/start channel_'):
        channel_msg_id = int(event.message.message.split('_')[-1])
        await client.forward_messages(event.sender_id, channel_msg_id, channel_id)
    await event.respond("❤️ BOT Share File Chúc bạn xem phim vui vẻ! \n \n <b>Copyright: @BotShareFilesTTG</b> \n \n Dùng /kichhoat để kích hoạt VIP Free.", parse_mode='html')

@client.on(events.NewMessage(func=lambda e: e.is_private))
async def handler(event):
    # Kiểm tra nếu tin nhắn bắt đầu bằng '/' thì không xử lý trong handler này
    if event.text.startswith('/'):
        return
    
    print("users_access main: ", users_access)
    
    if event.sender_id in users_access and datetime.datetime.now() < users_access[event.sender_id]:
        if event.media:
            caption = event.message.text if event.message.text else ""
            msg = await client.send_file(channel_id, event.media, caption=caption)
            start_link = f'https://t.me/{your_bot_username}?start=channel_{msg.id}'
            await event.respond(f'Link public của bạn đã được tạo: {start_link}', buttons=[Button.url('Xem Media', start_link)])
    else:
        await event.respond("Bạn cần kích hoạt truy cập để sử dụng chức năng này.")
                
if __name__ == '__main__':
    try:
        client.start(bot_token=bot_token)
        print("Khởi động BOT thành công!")

        async def initial_load():
            global activation_links, users_access  # Khai báo sử dụng biến toàn cục cho cả hai
            activation_links = await fetch_activation_links()  # Không cần gán lại nếu bạn muốn giữ giá trị toàn cục
            users_access = await load_users_access_from_api()  # Sửa đổi nếu bạn muốn giữ giá trị toàn cục

            print("activation_links khi khởi động lần đầu:", activation_links)
            print("users_access khi khởi động lần đầu:", users_access)

        client.loop.run_until_complete(initial_load())

        client.run_until_disconnected()
    except Exception as e:
        print(f'Lỗi không xác định: {e}')
