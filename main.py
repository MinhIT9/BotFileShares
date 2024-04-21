import datetime, random
from telethon import TelegramClient, events, Button
from datetime import timedelta

api_id = '21303563'
api_hash = '6ad9d81fb1c8e246de8255d7ecc449f5'
bot_token = '7068498391:AAHumK7nbOHxdYvn7B81aysNxyy3oSWam4Y'
your_bot_username = "sharefileTTGbot"
channel_id = -1002001373543

activation_links = {
    "12": {"url": "https://tiengioi.vip/Code1", "duration": 3},
    "13": {"url": "https://tiengioi.vip/Code2", "duration": 6},
    "14": {"url": "https://tiengioi.vip/Code3", "duration": 10},
    "15": {"url": "https://tiengioi.vip/Code4", "duration": 10},
    "16": {"url": "https://tiengioi.vip/Code5", "duration": 10},
    "17": {"url": "https://tiengioi.vip/Code6", "duration": 10}
}


# Theo dõi các mã đã được gửi để kích hoạt và thời gian hết hạn
pending_activations = {}
users_access = {}
# Tạo một từ điển mới để theo dõi link đã được phân phối cho người dùng nào
user_link_map = {}
# Đây là nơi chúng ta sẽ lưu trữ các link đã được phân phối
distributed_links = {}
LINK_DURATION = timedelta(minutes=1) #thời gian hết hạn link


client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Đây là hàm kiểm tra các kích hoạt đang chờ và nằm ở cấp độ module
def check_pending_activations():
    global pending_activations  # Sử dụng biến toàn cục
    current_time = datetime.datetime.now()
    expired_users = [user for user, expiry in pending_activations.items() if expiry < current_time]
    for user in expired_users:
        # Trả link vào pool chung
        if user in distributed_links:
            del distributed_links[user]
        del pending_activations[user]
        print(f"Activation link for user {user} has expired and is now available again.")

@client.on(events.NewMessage(pattern='/kichhoat'))
async def request_activation_link(event):
    check_pending_activations()
    current_time = datetime.datetime.now()

    # Kiểm tra xem người dùng đã nhận link chưa và link đó có còn hiệu lực không
    user_link_key = user_link_map.get(event.sender_id)
    if user_link_key:
        link_info = activation_links.get(user_link_key)
        link_expiry = pending_activations.get(event.sender_id)
        if link_info and link_expiry and current_time < link_expiry:
            await event.respond(
                f"Bạn đã yêu cầu kích hoạt trước đó và link vẫn còn hiệu lực. Vui lòng truy cập link sau để lấy mã kích hoạt của bạn: {link_info['url']}",
                buttons=[Button.url("Lấy mã kích hoạt", link_info['url'])]
            )
            return

    # Cấp phát link mới cho người dùng
    available_codes = [code for code in activation_links if code not in user_link_map.values()]
    if available_codes:
        random_code = random.choice(available_codes)
        link = activation_links[random_code]['url']
        user_link_map[event.sender_id] = random_code
        pending_activations[event.sender_id] = current_time + LINK_DURATION
        await event.respond(
            f"Để kích hoạt, vui lòng truy cập link sau và lấy mã kích hoạt của bạn: {link}",
            buttons=[Button.url("Lấy mã kích hoạt", link)]
        )
    else:
        await event.respond("Hiện không còn mã kích hoạt nào khả dụng. Vui lòng thử lại sau.")




@client.on(events.NewMessage(pattern='/code (.+)'))
async def activate_code(event):
    check_pending_activations()
    code = event.pattern_match.group(1).strip()
    current_time = datetime.datetime.now()

    if code in activation_links and (code not in distributed_links or distributed_links.get(code) == event.sender_id):
        code_info = activation_links[code]
        duration = timedelta(days=code_info["duration"])
        if event.sender_id in users_access and users_access[event.sender_id] > current_time:
            new_expiry_time = users_access[event.sender_id] + duration
        else:
            new_expiry_time = current_time + duration
        
        users_access[event.sender_id] = new_expiry_time
        distributed_links[code] = event.sender_id
        del activation_links[code]  # Xóa mã khỏi pool
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
    await event.respond("Chào mừng bạn đến với bot của chúng tôi! Dùng /kichhoat để kích hoạt truy cập.")

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
            await event.respond(f'Media của bạn đã được gửi. Click vào link này để xem: {start_link}', buttons=[Button.url('Xem Media', start_link)])
    else:
        await event.respond("Bạn cần kích hoạt truy cập để sử dụng chức năng này.")


# Bắt đầu client
print("Khởi chạy bot thành công!")
client.start(bot_token=bot_token)
client.run_until_disconnected()
