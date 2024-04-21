# api_utlis.py 

import requests
from config import USER_ACTIVATIONS_API

# Hàm lấy activation_links từ API
def load_activation_links(api_url):
    response = requests.get(api_url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to load activation links from API")
        return {}

def delete_code_from_api(code_id):
    try:
        response = requests.delete(f"{USER_ACTIVATIONS_API}/{code_id}")
        response.raise_for_status()
        print(f"Code with id {code_id} deleted successfully from API.")
    except requests.RequestException as e:
        print(f"Failed to delete code with id {code_id} from API: {e}")
        