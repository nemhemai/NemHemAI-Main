import time
from app.services.query_service import run_query

# Test query
query = "What are the rules for bulk waste generators?"
user = {"user_id": "test_user", "username": "test"}

print(f"\n--- Running test query: '{query}' ---")
start_time = time.time()
result = run_query(query, user)
latency = time.time() - start_time

print(f"\nLatency: {latency:.4f} seconds")
print(f"Confidence: {result.get('confidence')}")
print(f"\n=== ANSWER ===\n{result.get('answer_original')}\n==============")
if result.get('citations'):
    print(f"Top citation: {result['citations'][0].get('text', '')[:100]}...")
else:
    print("No citations found.")

