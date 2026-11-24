import os

IMMICH_URL = os.getenv("IMMICH_URL")
IMMICH_API_KEY = os.getenv("IMMICH_API_KEY")

print(f"IMMICH_URL: {IMMICH_URL}")
print(f"IMMICH_API_KEY: {IMMICH_API_KEY}")