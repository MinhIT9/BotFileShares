# main.py

from datetime import timedelta
import datetime, random, asyncio, threading, aiohttp, re
from config import Config  # Import class Config
from telethon import events, Button
from api_utlis import delete_code_from_api, fetch_activation_links, save_single_user_access_to_api, load_users_access_from_api, get_or_create_users_access_object, schedule_remove_expired_users_access
from config import (your_bot_username, channel_id, pending_activations, 
                    user_link_map, distributed_links, LINK_DURATION,
                    client, bot_token, USER_ACTIVATIONS_API)

# Gán biến mới cho users_access, activation_links 
config_instance = Config()
users_access = config_instance.users_access 
activation_links = config_instance.activation_links

# Hàm Kiểm Tra Hết Hạn Định Kỳ
LINK_DURATION_SECONDS = LINK_DURATION.total_seconds()
async def check_and_restore_expired_links():
    while True:
        current_time = datetime.datetime.now()
        expired_users = []
        for user, expiry in list(pending_activations.items()):
            if expiry < current_time:
                expired_users.append(user)
                code = user_link_map.get(user)
                if code:
                    # Trả mã về pool nếu hết hạn
                    activation_links[code] = distributed_links.pop(code, None)
                    user_link_map.pop(user, None)

        for user in expired_users:
            pending_activations.pop(user, None)

        if expired_users:
            print(f"Các link kích hoạt cho {expired_users} đã hết hạn và giờ đây đã sẵn sàng trở lại.")

        await asyncio.sleep(LINK_DURATION_SECONDS)

# Đây là hàm kiểm tra các kích hoạt đang chờ và nằm ở cấp độ module
def check_pending_activations():
    current_time = datetime.datetime.now()
    expired_users = []
    for user, expiry in list(pending_activations.items()):
        if expiry < current_time:
            expired_users.append(user)
            code = user_link_map.get(user)
            if code:
                # Trả mã về pool nếu hết hạn
                activation_links[code] = distributed_links[code]
                user_link_map.pop(user, None)
                distributed_links.pop(code, None)

    for user in expired_users:
        pending_activations.pop(user, None)

    if expired_users:
        print(f"Các link kích hoạt cho {expired_users} đã hết hạn và giờ đây đã sẵn sàng trở lại.")

# Hàm này được gọi khi người dùng yêu cầu link kích hoạt mới hoặc khi họ không phải VIP
async def provide_new_activation_link(event, current_time):
    available_codes = [code for code in activation_links if code not in user_link_map.values()]
    if available_codes:
        random_code = random.choice(available_codes)
        link_info = activation_links[random_code]
        link = link_info['url']
        link_backup = link_info.get('backup_url', 'Không có link dự phòng')
        response_text = (f"Link kích hoạt mới của bạn: {link}\n"
                         f"Link dự phòng: {link_backup}")
        user_link_map[event.sender_id] = random_code
        pending_activations[event.sender_id] = current_time + LINK_DURATION
        await event.respond(response_text, buttons=[Button.url("Kích hoạt", link)], parse_mode='html')
    else:
        await event.respond("Hiện tại không có mã kích hoạt nào khả dụng. Vui lòng thử lại sau.")

async def provide_activation_link(event, renewing=False):
    current_time = datetime.datetime.now()
    user_id = event.sender_id

    # Kiểm tra và cập nhật các link đã hết hạn
    check_pending_activations()

    # Nếu đang gia hạn và người dùng có link chưa hết hạn
    if renewing and user_id in user_link_map and current_time < pending_activations[user_id]:
        code = user_link_map[user_id]
        link_info = activation_links[code]
        response_text = (f"Link kích hoạt của bạn vẫn còn hiệu lực: {link_info['url']}\n"
                         f"Link dự phòng: {link_info.get('backup_url', 'Không có link dự phòng')}")
        await event.respond(response_text, buttons=[Button.url("Kích hoạt", link_info['url'])], parse_mode='html')
        return

    # Xử lý cấp link mới
    available_codes = [code for code in activation_links if code not in distributed_links]
    if available_codes:
        chosen_code = random.choice(available_codes)
        link_info = activation_links[chosen_code]
        response_text = (f"Link kích hoạt mới của bạn: {link_info['url']}\n"
                         f"Link dự phòng: {link_info.get('backup_url', 'Không có link dự phòng')}")
        pending_activations[user_id] = current_time + LINK_DURATION
        user_link_map[user_id] = chosen_code
        distributed_links[chosen_code] = user_id

        await event.respond(response_text, buttons=[Button.url("Kích hoạt", link_info['url'])], parse_mode='html')
    else:
        await event.respond("Hiện tại không có mã kích hoạt nào khả dụng. Vui lòng thử lại sau.")

        
# Xác định regex cho lệnh thêm code
@client.on(events.NewMessage(pattern=r'/newcodettgs ([\s\S]+)'))
async def add_new_code(event):
    codes_data = event.pattern_match.group(1)
    codes_lines = codes_data.strip().split('\n')
    
    for line in codes_lines:
        parts = line.strip().split()
        if len(parts) == 4:
            # Tạo payload cho API
            code, link, backup_link, duration = parts
            payload = {
                'Code': code,
                'Link': link,
                'LinkBackup': backup_link,
                'duration': int(duration)
            }
            
            # Thêm vào pool tạm thời trước
            activation_links[code] = {
                'url': link,
                'backup_url': backup_link,
                'duration': int(duration)
            }
            
            # Cập nhật API
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(USER_ACTIVATIONS_API, json=payload) as response:
                        if response.status == 201:
                            await event.respond(f"Thêm mã thành công: {payload['Code']}")
                        else:
                            error_message = await response.text()
                            # Nếu thêm vào API không thành công, xóa khỏi pool tạm thời
                            activation_links.pop(code, None)
                            await event.respond(f"Không thể thêm mã {payload['Code']}: {error_message}")
                except aiohttp.ClientError as e:
                    # Nếu thêm vào API không thành công, xóa khỏi pool tạm thời
                    activation_links.pop(code, None)
                    await event.respond(f"Lỗi kết nối API: {str(e)}")
        else:
            await event.respond("Định dạng dữ liệu không đúng. Cần có 4 phần: code, link chính, link dự phòng và thời hạn.")
                
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
    for code, code_info in activation_links.items():
        # Kiểm tra kiểu dữ liệu trước khi truy cập 'duration'
        if isinstance(code_info, dict) and 'duration' in code_info:
            duration = code_info['duration']
            if duration in duration_counts:
                duration_counts[duration] += 1
            else:
                duration_counts[duration] = 1
        else:
            print(f"Unexpected data type for code '{code}' in activation_links: {type(code_info)}")
            continue  # Skip this iteration if the data type is not as expected
    
    # Tạo và gửi thông báo về số lượng mã theo từng thời hạn
    response_message = "<b>Tình trạng mã kích hoạt VIP hiện tại:</b>\n"
    for duration, count in sorted(duration_counts.items()):
        response_message += f"Code VIP: <b>{duration} ngày</b> - còn lại: <b>{count} mã</b>\n"
    
    # Thêm thông báo hướng dẫn sử dụng /kichhoat
    response_message += "\nMã hoàn toàn ngẫu nhiên, nên chúc các bạn may mắn nhé!\n\n👍 Sử dụng <b>/kichhoat</b> để lấy mã kích hoạt VIP.\n\nBản quyền thuộc về @BotShareFilesTTG"

    # Kiểm tra nếu có mã khả dụng để gửi phản hồi
    if duration_counts:
        await event.respond(response_message, parse_mode='html')
    else:
        await event.respond("Hiện không có mã kích hoạt nào khả dụng.")


@client.on(events.NewMessage(pattern='/kichhoat'))
async def request_activation_link(event):
    user_id = event.sender_id
    current_time = datetime.datetime.now()

    # Kiểm tra xem người dùng đã là VIP và thông báo hạn sử dụng còn lại
    if user_id in users_access and current_time < users_access[user_id]:
        expiry_str = users_access[user_id].strftime('%H:%M %d-%m-%Y')
        await event.respond(
            f"Bạn đã là VIP và hạn sử dụng đến: {expiry_str}. Sử dụng /giahan để tăng thời gian sử dụng VIP."
        )
        return

    # Kiểm tra xem người dùng có link hết hạn không
    if user_id in pending_activations and current_time < pending_activations[user_id]:
        code = user_link_map[user_id]
        link_info = activation_links[code]
        link = link_info['url']
        link_backup = link_info.get('backup_url', 'Không có link dự phòng')
        response_text = (f"Link kích hoạt của bạn vẫn còn hiệu lực: {link}\n"
                        f"Link dự phòng: {link_backup}")
        await event.respond(response_text)
        return

    # Cung cấp link mới nếu không có link hoặc link đã hết hạn
    await provide_activation_link(event, renewing=False)
        
# Hàm này sẽ được gọi khi user đã là VIP và muốn gia hạn sử dụng
@client.on(events.NewMessage(pattern='/giahan'))
async def renew_vip(event):
    user_id = event.sender_id
    current_time = datetime.datetime.now()

    # Kiểm tra xem người dùng đã là VIP chưa và cung cấp tùy chọn gia hạn
    if user_id in users_access and current_time < users_access[user_id]:
        await provide_activation_link(event, renewing=True)
    else:
        await event.respond("Chức năng này chỉ dành cho VIP. Sử dụng /kichhoat để trở thành VIP.")

        
@client.on(events.NewMessage(pattern=r'/code (\d+)'))
async def activate_code(event):
    user_id = event.sender_id
    code_entered = event.pattern_match.group(1).strip()
    current_time = datetime.datetime.now()

    # Kiểm tra mã nhập hợp lệ và chưa hết hạn
    if code_entered in activation_links and code_entered in user_link_map.values() and user_id in pending_activations and current_time < pending_activations[user_id]:
        code_info = activation_links.pop(code_entered)
        duration = timedelta(days=code_info['duration'])
        expiry_time = users_access.get(user_id, current_time)
        new_expiry_time = expiry_time + duration

        users_access[user_id] = new_expiry_time
        distributed_links.pop(code_entered, None)
        pending_activations.pop(user_id, None)

        # Cập nhật thông tin truy cập vào API
        access_object = await get_or_create_users_access_object()
        access_object["users_access"][str(user_id)] = new_expiry_time.isoformat()
        await save_single_user_access_to_api(access_object)

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
    user_id = event.sender_id
    current_time = datetime.datetime.now()

    # Kiểm tra nếu tin nhắn bắt đầu bằng '/' thì xử lý các lệnh đặc biệt
    if event.text.startswith('/'):
        # Bỏ qua để xử lý lệnh trong các sự kiện khác
        return
    
    # Kiểm tra xem người dùng có phải VIP không
    is_vip = user_id in users_access and current_time < users_access[user_id]

    # Định dạng link mong muốn
    expected_link_format = f'https://t.me/{your_bot_username}?start=channel_'

    # Xử lý tin nhắn là link dạng mong muốn
    if event.text.startswith(expected_link_format):
        channel_msg_id_str = event.text[len(expected_link_format):]
        if channel_msg_id_str.isdigit():
            channel_msg_id = int(channel_msg_id_str)
            try:
                message = await client.get_messages(channel_id, ids=channel_msg_id)
                if message:
                    await client.forward_messages(event.sender_id, message.id, channel_id)
                    # Gửi thông báo đặc biệt kèm theo
                    await event.respond("Bot chia sẻ file PRO: @BotShareFilesTTG")
                else:
                    await event.respond("Link không hợp lệ hoặc đã hết hạn.")
            except Exception as e:
                await event.respond(f"Không thể truy cập nội dung tin nhắn: {str(e)}")
        else:
            await event.respond("Link không hợp lệ hoặc đã hết hạn.")
    # Xử lý tin nhắn là media từ người dùng VIP
    elif event.media and is_vip:
        caption = event.message.text if event.message.text else ""
        msg = await client.send_file(channel_id, event.media, caption=caption)
        start_link = f'https://t.me/{your_bot_username}?start=channel_{msg.id}'
        await event.respond(f'Link công khai của bạn đã được tạo: {start_link}', buttons=[Button.url('Xem Media', start_link)])
    # Người dùng không phải VIP gửi media hoặc text không đúng định dạng link mong muốn
    else:
        await event.respond("Bạn cần kích hoạt VIP để sử dụng chức năng này. \n Bấm /kichhoat để trở thành thành viên VIP.")

async def initial_load():
    global activation_links, users_access
    activation_links = await fetch_activation_links()
    users_access = await load_users_access_from_api()

if __name__ == '__main__':
    try:
        client.start(bot_token=bot_token)
        print("Khởi động BOT thành công!")
        
        # Thêm lịch trình xóa người dùng hết hạn từ api_utils.
        client.loop.create_task(schedule_remove_expired_users_access())
        client.loop.create_task(check_and_restore_expired_links())

        client.loop.run_until_complete(initial_load())
        client.run_until_disconnected()
    except Exception as e:
        print(f'Lỗi không xác định: {e}')