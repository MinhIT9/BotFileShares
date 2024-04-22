# main.py

import datetime, random, requests, threading, asyncio, aiohttp
from telethon import events, Button
from datetime import timedelta
from api_utlis import delete_code_from_api
from config import (your_bot_username, channel_id, pending_activations,users_access, 
                    user_link_map, distributed_links, LINK_DURATION, activation_links,
                    client, bot_token, USER_ACTIVATIONS_API)

# Hàm async để cập nhật activation_links từ API
async def update_activation_links_periodically():
    while True:
        try:
            # Gọi hàm đồng bộ trong một thread khác
            new_activation_links = await client.loop.run_in_executor(None, fetch_activation_links)
            if new_activation_links:
                # Cập nhật activation_links global
                global activation_links
                activation_links = new_activation_links
                print(f"Activation links updated at {datetime.datetime.now()}.")
                print(activation_links)
        except Exception as e:
            print(f"Error fetching activation links: {e}")
        
        # Chờ 10 phút trước khi chạy lại hàm
        await asyncio.sleep(3600)

# Hàm đồng bộ để lấy activation_links từ API
def fetch_activation_links():
    response = requests.get(USER_ACTIVATIONS_API)
    if response.status_code == 200:
        return {item['Code']: {'url': item['Link'], 'duration': item['duration'], 'id': item['id']} for item in response.json()}
    else:
        return None

# Đây là hàm kiểm tra các kích hoạt đang chờ và nằm ở cấp độ module
def check_pending_activations():
    global pending_activations, activation_links, user_link_map  # Sử dụng biến toàn cục
    current_time = datetime.datetime.now()
    expired_users = []

    # Kiểm tra xem mã kích hoạt nào đã hết hạn và cần được trả lại pool
    for user, expiry in pending_activations.items():
        if expiry < current_time:
            expired_users.append(user)
            code = user_link_map.get(user)
            if code:
                # Chỉ trả mã kích hoạt trở lại pool nếu nó còn tồn tại trong distributed_links
                if code in distributed_links:
                    activation_links[code] = distributed_links[code]
                # Loại bỏ người dùng khỏi các bản đồ
                user_link_map.pop(user, None)

    # Xóa người dùng khỏi pending_activations và distributed_links
    for user in expired_users:
        pending_activations.pop(user, None)
        distributed_links.pop(user, None)

    # Lưu ý cho người dùng quản trị biết mã nào đã được trả lại pool
    if expired_users:
        print(f"Activation links for users {expired_users} have expired and are now available again.")


async def provide_new_activation_link(event, current_time):
    # Chọn một mã ngẫu nhiên từ pool không được sử dụng
    available_codes = [code for code in activation_links if code not in user_link_map.values()]
    if available_codes:
        random_code = random.choice(available_codes)
        link = activation_links[random_code]['url']
        # Cập nhật thông tin cho người dùng
        user_link_map[event.sender_id] = random_code
        pending_activations[event.sender_id] = current_time + LINK_DURATION
        # Gửi link mới
        await event.respond(
            f"<b>Để kích hoạt</b>, vui lòng vào link sau và lấy mã kích hoạt của bạn: <b>{link}</b> \n \n👌 Các lệnh có thể sử dụng: \n<b>/kichhoat</b> : Dùng để lấy Link CODE \n<b>/code MaCuaBan </b> : ví dụ: <b>/code 12345</b> nhấn enter để kích hoạt \n\n<b>/checkcode</b> : Để xem còn bao nhiều CODE VIP bên trong BOT",
            buttons=[Button.url("Lấy mã kích hoạt", link)],parse_mode='html'
        )
    else:
        await event.respond("Hiện không còn mã kích hoạt nào khả dụng. Vui lòng thử lại sau.")
        
        
# Xác định regex cho lệnh mới
@client.on(events.NewMessage(pattern='/newcodettgs ([\s\S]+)'))
async def add_new_code(event):
    # Ghi nhận bắt đầu xử lý lệnh
    print("Received new code addition request")
    # Tách nội dung thành các dòng
    codes_data = event.pattern_match.group(1)
    codes_lines = codes_data.strip().split('\n')
    
    async with aiohttp.ClientSession() as session:
        for line in codes_lines:
            parts = line.strip().split()
            if len(parts) == 3:
                # Tạo từ điển cho dữ liệu JSON
                payload = {
                    'Code': parts[0],
                    'Link': parts[1],
                    'duration': int(parts[2])
                }
                try:
                    # Ghi nhận chi tiết yêu cầu gửi đi
                    print(f"Attempting to add new code: {payload}")
                    # Thực hiện POST request
                    async with session.post(USER_ACTIVATIONS_API, json=payload) as response:
                        if response.status == 201:
                            await event.respond(f"Đã thêm thành công: {payload['Code']}")
                            print(f"Successfully added code: {payload['Code']}")
                        else:
                            # Đọc phản hồi lỗi từ API
                            error_message = await response.text()
                            await event.respond(f"Không thể thêm code {payload['Code']}: {error_message}")
                            print(f"Failed to add code {payload['Code']}: {error_message}")
                except aiohttp.ClientError as e:
                    await event.respond(f"Lỗi khi kết nối với API: {str(e)}")
                    print(f"API connection error: {str(e)}")
            else:
                await event.respond(f"Định dạng không đúng: {line}")
                print(f"Incorrect format for line: {line}")
                
@client.on(events.NewMessage(pattern='/updatecode'))
async def handle_update_code_command(event):
    # Gọi hàm cập nhật code từ API ngay lập tức
    print("Received request to update codes immediately.")
    try:
        new_activation_links = await client.loop.run_in_executor(None, fetch_activation_links)
        if new_activation_links:
            # Cập nhật activation_links global
            global activation_links
            activation_links = new_activation_links
            await event.respond("Cập nhật mã kích hoạt thành công!")
            print(f"Activation links updated at {datetime.datetime.now()}.")
            print(activation_links)
        else:
            await event.respond("Không thể cập nhật mã kích hoạt từ API.")
            print("Failed to fetch activation links from API.")
    except Exception as e:
        await event.respond(f"Lỗi khi cập nhật mã: {str(e)}")
        print(f"Error updating activation links: {e}")                


@client.on(events.NewMessage(pattern='/checkcode'))
async def check_code_availability(event):
    # Đếm số lượng mã theo từng thời hạn sử dụng
    duration_counts = {}
    for code_info in activation_links.values():
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


@client.on(events.NewMessage(pattern='/kichhoat'))
async def request_activation_link(event):
    check_pending_activations()
    current_time = datetime.datetime.now()

    # Xử lý cho người dùng đã kích hoạt VIP
    if event.sender_id in users_access and users_access[event.sender_id] > current_time:
        await provide_new_activation_link(event, current_time)
        return

    # Kiểm tra xem người dùng đã nhận link chưa và link đó có còn hiệu lực không
    if event.sender_id in pending_activations:
        if current_time < pending_activations[event.sender_id]:
            # Nếu link vẫn còn hiệu lực, thông báo cho người dùng
            code = user_link_map[event.sender_id]
            link = activation_links[code]['url']
            await event.respond(
                f"Bạn đã yêu cầu kích hoạt trước đó và link vẫn còn hiệu lực. Vui lòng truy cập link sau để lấy mã kích hoạt của bạn: {link}",
                buttons=[Button.url("Lấy mã kích hoạt", link)], parse_mode='html'
            )
        else:
            # Link đã hết hạn, cung cấp link mới
            await provide_new_activation_link(event, current_time)
    else:
        # Người dùng chưa có link, cung cấp link mới
        await provide_new_activation_link(event, current_time)

@client.on(events.NewMessage(pattern='/code (.+)'))
async def activate_code(event):
    check_pending_activations()
    code = event.pattern_match.group(1).strip()
    current_time = datetime.datetime.now()

    # Kiểm tra xem code có trong activation_links và chưa được phân phối hoặc đã được phân phối cho sender_id hiện tại
    if code in activation_links and (code not in distributed_links or distributed_links.get(code) == event.sender_id):
        code_info = activation_links[code]
        duration = timedelta(days=code_info["duration"])
        new_expiry_time = users_access.get(event.sender_id, current_time) + duration
        
        users_access[event.sender_id] = new_expiry_time
        distributed_links[code] = event.sender_id
        
        # Kích hoạt mã và lấy id để xóa trên API
        code_id = code_info['id']  # Giả sử mỗi entry có 'id'
        
        del activation_links[code]  # Xóa mã khỏi pool
        
        # Xóa mã khỏi API
        threading.Thread(target=delete_code_from_api, args=(code_id,)).start()
        
        print("activation_links after deletion: ", activation_links)
        await event.respond(f"Bạn đã kích hoạt thành công! Thời gian sử dụng mới của bạn là {new_expiry_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    else:
        await event.respond("Mã kích hoạt không hợp lệ hoặc đã được sử dụng.")

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
    
    if event.sender_id in users_access and datetime.datetime.now() < users_access[event.sender_id]:
        if event.media:
            caption = event.message.text if event.message.text else ""
            msg = await client.send_file(channel_id, event.media, caption=caption)
            start_link = f'https://t.me/{your_bot_username}?start=channel_{msg.id}'
            await event.respond(f'Link public của bạn đã được tạo: {start_link}', buttons=[Button.url('Xem Media', start_link)])
    else:
        await event.respond("Bạn cần kích hoạt truy cập để sử dụng chức năng này.")

# Bắt đầu client
client.start(bot_token=bot_token)

# Hàm main chính để khởi động bot
if __name__ == '__main__':
    # Cập nhật activation_links từ API khi bot khởi động
    activation_links.update(fetch_activation_links())
    
    # Thêm hàm cập nhật định kỳ vào loop
    client.loop.create_task(update_activation_links_periodically())
    
    print("Khởi chạy bot thành công!")
    client.run_until_disconnected()