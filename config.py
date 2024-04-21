# config.py
from datetime import timedelta
from telethon import TelegramClient

api_id = '21303563'
api_hash = '6ad9d81fb1c8e246de8255d7ecc449f5'

# DEV
# bot_token = '7068498391:AAHumK7nbOHxdYvn7B81aysNxyy3oSWam4Y'
# your_bot_username = "sharefileTTGbot"
# channel_id = -1002001373543

bot_token="6737137775:AAEGBx0Y8jlV-7QxQvAIUvwU3BOpqYifSC8"
your_bot_user = "@ShareFileVIPSbot"
channel_id = -1002132651013

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

USER_ACTIVATIONS_API = "https://6624929304457d4aaf9c7cd6.mockapi.io/activation_links"


# Theo dõi các mã đã được gửi để kích hoạt và thời gian hết hạn
pending_activations = {}
# Lưu trữ thông tin về thời gian hết hạn kích hoạt của từng người dùng
users_access = {}
# Tạo một từ điển mới để theo dõi link đã được phân phối cho người dùng nào
user_link_map = {}
# Đây là nơi chúng ta sẽ lưu trữ các link đã được phân phối
distributed_links = {}

LINK_DURATION = timedelta(minutes=6) #thời gian hết hạn link

activation_links = {}
