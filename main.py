from telethon import TelegramClient, events, Button
import datetime

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


@client.on(events.NewMessage(pattern='/start'))
async def send_welcome(event):
    check_pending_activations()
    # Kiểm tra payload từ link /start để xác định xem có cần forward tin nhắn từ channel không
    if event.message.message.startswith('/start channel_'):
        channel_msg_id = int(event.message.message.split('_')[-1])
        await client.forward_messages(event.sender_id, channel_msg_id, channel_id)
    await event.respond("Chào mừng bạn đến với bot của chúng tôi! Dùng /kichhoat để kích hoạt truy cập.")


@client.on(events.NewMessage(pattern='/kichhoat'))
async def send_activation_link(event):
    check_pending_activations()
    # Tìm link chưa được phân phối
    available_link = None
    for code, link in activation_links.items():
        if link not in distributed_links.values():
            available_link = link
            break
    
    # Nếu tất cả các link đều đã được phân phối
    if not available_link:
        await event.respond("Hiện tất cả các mã kích hoạt đều đang được sử dụng, vui lòng thử lại sau.")
    else:
        # Phân phối link và thiết lập thời gian hết hạn
        distributed_links[event.sender_id] = available_link
        pending_activations[event.sender_id] = datetime.datetime.now() + datetime.timedelta(minutes=10)
        await event.respond(
            f"Để kích hoạt, vui lòng truy cập link sau: {available_link}",
            buttons=[Button.url("Lấy mã kích hoạt", available_link)]
        )

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
