from dotenv import load_dotenv
import os
import ngrok
import time

load_dotenv()

listener = ngrok.forward(
    8501,
    authtoken=os.getenv("NGROK_AUTHTOKEN"),
    traffic_policty='{"on_http_request":[{"actions": [{"type": "oauth","config": {"provider": "google"}}]}]}'
)

print(f"Ingress established at {listener.url()}")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Closing listener")