import requests
import time

res = requests.post(
    "http://localhost:8000/api/v1/entitlement",
    json={"citizen_id": "CIT-123", "raw_query": "I am a farmer"}
)
print("POST Status:", res.status_code)
data = res.json()
query_id = data.get("query_id")
print("Query ID:", query_id)

while True:
    time.sleep(2)
    poll_res = requests.get(f"http://localhost:8000/api/v1/entitlement/{query_id}")
    if poll_res.status_code != 200:
        print("GET failed:", poll_res.status_code)
        break
    poll_data = poll_res.json()
    status = poll_data.get("status")
    print("Status:", status)
    if status != "PROCESSING":
        print("Final Data keys:", poll_data.keys())
        det = poll_data.get("determination", {})
        print("Determination keys:", det.keys())
        if "schemes" in det:
            print("Schemes length:", len(det["schemes"]))
            if len(det["schemes"]) > 0:
                print("First scheme keys:", det["schemes"][0].keys())
                print("First scheme:", det["schemes"][0]["scheme_name"])
        break
