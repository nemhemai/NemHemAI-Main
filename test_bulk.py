import requests

url = "http://127.0.0.1:8000/api/bulk-upload"
headers = {
    # Provide a dummy token if auth is required, but let's see what it says
    "Authorization": "Bearer TEST"
}

# Create dummy files
with open("test1.pdf", "wb") as f:
    f.write(b"%PDF-1.4 dummy")
with open("test1.json", "w") as f:
    f.write('{"title": "test"}')

files = [
    ('files', ('test1.pdf', open('test1.pdf', 'rb'), 'application/pdf')),
    ('metadata_files', ('test1.json', open('test1.json', 'rb'), 'application/json'))
]

response = requests.post(url, headers=headers, files=files)
print(response.status_code)
print(response.text)
