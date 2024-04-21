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


@client.on(events.NewMessage(pattern='/kichhoat(?: (.*))?'))
async def send_activation_link(event):
    check_pending_activations()
    args = event.pattern_match.group(1)

    if args:
        # Người dùng đã nhập mã kích hoạt
        code = args.strip()
        if code in activation_links and code in distributed_links and distributed_links[code] == event.sender_id:
            # Kích hoạt mã nếu mã đúng và được phân phối cho người dùng này
            users_access[event.sender_id] = datetime.datetime.now() + datetime.timedelta(days=30) # Thời gian truy cập sau khi kích hoạt
            del distributed_links[code]  # Xóa người dùng khỏi danh sách distributed_links
            del pending_activations[event.sender_id]  # Xóa người dùng khỏi danh sách pending_activations
            await event.respond("Bạn đã kích hoạt thành công! Bây giờ bạn có thể sử dụng các chức năng của bot.")
        else:
            await event.respond("Mã kích hoạt không hợp lệ hoặc đã được sử dụng.")
    else:
        # Nếu không có mã được cung cấp, phân phối link kích hoạt
        available_code = None
        for code, link in activation_links.items():
            if code not in distributed_links:
                available_code = code
                break
        
        if not available_code:
            await event.respond("Hiện tất cả các mã kích hoạt đều đang được sử dụng, vui lòng thử lại sau.")
        else:
            distributed_links[available_code] = event.sender_id
            pending_activations[event.sender_id] = datetime.datetime.now() + datetime.timedelta(minutes=10)
            await event.respond(
                f"Để kích hoạt, vui lòng truy cập link sau và lấy mã kích hoạt của bạn: {activation_links[available_code]}",
                buttons=[Button.url("Lấy mã kích hoạt", activation_links[available_code])]
            )




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
