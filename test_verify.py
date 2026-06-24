import requests
from io import BytesIO
from PIL import Image

# Create a dummy image
img = Image.new('RGB', (100, 100), color = 'red')
img_byte_arr = BytesIO()
img.save(img_byte_arr, format='PNG')
img_byte_arr.seek(0)

# Make the request
url = "http://localhost:8000/api/v1/verification/verify-pipeline"
files = {'file': ('dummy.png', img_byte_arr, 'image/png')}
response = requests.post(url, files=files)
print("Status Code:", response.status_code)
print("Response JSON:", response.text)
