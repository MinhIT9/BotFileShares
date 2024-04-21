from telethon import TelegramClient, events, Button

api_id = '21303563'
api_hash = '6ad9d81fb1c8e246de8255d7ecc449f5'
bot_token = '7068498391:AAHumK7nbOHxdYvn7B81aysNxyy3oSWam4Y'
your_bot_username = "sharefileTTGbot"
channel_id = -1002001373543

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

@client.on(events.NewMessage(pattern='/start'))
async def send_welcome(event):
    # Kiểm tra payload từ link /start để xác định xem có cần forward tin nhắn từ channel không
    if event.message.message.startswith('/start channel_'):
        channel_msg_id = int(event.message.message.split('_')[-1])
        await client.forward_messages(event.sender_id, channel_msg_id, channel_id)

@client.on(events.NewMessage(func=lambda e: e.is_private))
async def handler(event):
    # Xử lý tin nhắn có chứa media như ảnh hoặc video
    if event.media:
        # Lấy caption từ tin nhắn, nếu có
        caption = event.message.text if event.message.text else ""
        # Gửi media kèm caption vào channel và lấy message ID
        msg = await client.send_file(channel_id, event.media, caption=caption)
        # Tạo link động cho người dùng để xem lại media thông qua bot
        start_link = f'https://t.me/{your_bot_username}?start=channel_{msg.id}'
        await event.respond(f'Media của bạn đã được gửi. Click vào link này để xem: {start_link}', buttons=[Button.url('Xem Media', start_link)])


# Bắt đầu client
print("Khởi chạy bot thành công!")
client.start(bot_token=bot_token)
client.run_until_disconnected()
