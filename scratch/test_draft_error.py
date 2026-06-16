import sys
sys.path.insert(0, '.')
from app.generation.draft_generator import generate_draft_response
import logging

logging.basicConfig(level=logging.INFO)

print("Calling generate_draft_response...")
try:
    res = generate_draft_response(
        citizen_id="0ef48e6d-9fc9-4821-91d0-53895cb422ae",
        category="Roads",
        description="I would like to report a massive pothole that has developed on the main arterial road connecting the Civil Hospital to the downtown market area. Because of the recent monsoon rains, the pothole has expanded significantly and is now a major hazard for two-wheelers, especially at night when the streetlights are dim. Could the public works department please schedule a patch repair job here within the next week to prevent any accidents"
    )
    print("Result:")
    print(res)
except Exception as e:
    print("Failed with exception:", e)
