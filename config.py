# config.py
from datetime import timedelta
from telethon import TelegramClient

api_id = '21303563'
api_hash = '6ad9d81fb1c8e246de8255d7ecc449f5'

# DEV
bot_token = '7068498391:AAHumK7nbOHxdYvn7B81aysNxyy3oSWam4Y'
your_bot_username = "sharefileTTGbot"
channel_id = -1002001373543
USER_ACTIVATIONS_API = "https://6626aa5f052332d553239fd6.mockapi.io/activation_links"
USERS_ACCESS_API="https://6626aa5f052332d553239fd6.mockapi.io/Account"

# bot_token="6737137775:AAEGBx0Y8jlV-7QxQvAIUvwU3BOpqYifSC8"
# your_bot_username = "ShareFileVIPSbot"
# channel_id = -1002132651013
# USER_ACTIVATIONS_API = "https://6624929304457d4aaf9c7cd6.mockapi.io/activation_links"
# USERS_ACCESS_API=""

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Theo dõi các mã đã được gửi để kích hoạt và thời gian hết hạn
pending_activations = {}
# Tạo một từ điển mới để theo dõi link đã được phân phối cho người dùng nào
user_link_map = {}
# Đây là nơi chúng ta sẽ lưu trữ các link đã được phân phối
distributed_links = {}

LINK_DURATION = timedelta(minutes=0.5) #thời gian hết hạn link theo phút

class Config:
    _instance = None

    def __init__(self):
        self.activation_links = {}
        self.users_access = {}

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.__init__()  # Gọi hàm khởi tạo
        return cls._instance

