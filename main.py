import datetime
from telethon import TelegramClient, events, Button
from datetime import timedelta

api_id = '21303563'
api_hash = '6ad9d81fb1c8e246de8255d7ecc449f5'
bot_token = '7068498391:AAHumK7nbOHxdYvn7B81aysNxyy3oSWam4Y'
your_bot_username = "sharefileTTGbot"
channel_id = -1002001373543

# Lưu trữ các link để lấy mã
activation_links = {
    "123": "https://tiengioi.vip/Code1",
    "234": "https://tiengioi.vip/Code2",
    "456": "https://tiengioi.vip/Code3"
}

# Theo dõi các mã đã được gửi để kích hoạt và thời gian hết hạn
pending_activations = {}
users_access = {}
# Đây là nơi chúng ta sẽ lưu trữ các link đã được phân phối
distributed_links = {}
# Đặt thời gian kích hoạt cơ bản là 3 ngày
BASIC_ACTIVATION_DURATION = timedelta(days=3)
LINK_DURATION = timedelta(minutes=4) #thời gian hết hạn link


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

    # Kiểm tra nếu người dùng đã kích hoạt và có quyền truy cập
    if event.sender_id in users_access and users_access[event.sender_id] > current_time:
        code, link = next((item for item in activation_links.items() if item[0] not in distributed_links), (None, None))
        if code:
            distributed_links[event.sender_id] = link
            pending_activations[event.sender_id] = current_time + LINK_DURATION
            await event.respond(
                f"Bạn đã kích hoạt trước đó. Đây là link mới để lấy mã kích hoạt bổ sung: {link}",
                buttons=[Button.url("Lấy mã kích hoạt bổ sung", link)]
            )
        else:
            await event.respond("Hiện không còn mã kích hoạt nào khả dụng. Vui lòng thử lại sau.")
        return

    # Kiểm tra nếu link kích hoạt đã được gửi trước đó và vẫn còn hiệu lực
    if event.sender_id in pending_activations:
        link = distributed_links[event.sender_id]
        link_expiry = pending_activations[event.sender_id]
        if current_time < link_expiry:
            await event.respond(
                f"Bạn đã yêu cầu kích hoạt trước đó. Vui lòng truy cập link sau để lấy mã kích hoạt của bạn: {link}",
                buttons=[Button.url("Lấy mã kích hoạt", link)]
            )
        else:
            code, link = next((item for item in activation_links.items() if item[0] not in distributed_links), (None, None))
            if code:
                distributed_links[event.sender_id] = link
                pending_activations[event.sender_id] = current_time + LINK_DURATION
                await event.respond(
                    f"Link đã hết hạn, đây là link mới để lấy mã kích hoạt: {link}",
                    buttons=[Button.url("Lấy mã kích hoạt", link)]
                )
            else:
                await event.respond("Hiện không còn mã kích hoạt nào khả dụng. Vui lòng thử lại sau.")
    else:
        code, link = next((item for item in activation_links.items() if item[0] not in distributed_links), (None, None))
        if code:
            distributed_links[event.sender_id] = link
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

    # Kiểm tra mã kích hoạt có hợp lệ và chưa được sử dụng hoặc đã sử dụng bởi người dùng này
    if code in activation_links and (code not in distributed_links or distributed_links.get(code) == event.sender_id):
        # Kiểm tra xem người dùng đã có quyền truy cập trước đó chưa và thời gian sử dụng còn lại
        if event.sender_id in users_access and users_access[event.sender_id] > current_time:
            new_expiry_time = users_access[event.sender_id] + BASIC_ACTIVATION_DURATION
        else:
            new_expiry_time = current_time + BASIC_ACTIVATION_DURATION
            
        users_access[event.sender_id] = new_expiry_time
        distributed_links[code] = event.sender_id
        del activation_links[code]
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
