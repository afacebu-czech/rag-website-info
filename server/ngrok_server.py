import sys
import signal
import torch
from pyngrok import ngrok


class NgrokServer:
    def __init__(self, ngrok_token=None):
        self.ngrok_token = ngrok_token
        
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)

        self.tunnel = None

    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n" + "=" * 50)
        print("Shutting down gracefully...")
        print("=" * 50)

        # Close ngrok tunnel if running
        if self.tunnel:
            ngrok.disconnect(self.tunnel.public_url)
            ngrok.kill()
            print("✓ ngrok tunnel closed")

        # Clear GPU cache if using GPU
        if self.device_config["device_type"] == "CUDA GPU":
            torch.cuda.empty_cache()
            print("✓ GPU cache cleared")

        print("✓ Server stopped")
        sys.exit(0)

    def run_server(self, app):
        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("\n" + "=" * 50)
        print("Starting Whisper Transcription Server (ngrok mode)...")
        print("=" * 50)
        print("Press Ctrl+C to stop the server")
        print("=" * 50 + "\n")

        try:
            # Start ngrok tunnel
            self.tunnel = ngrok.connect(7860, "http")

            print("\n" + "=" * 70)
            print("🌐 Public Server Access (ngrok)")
            print("=" * 70)
            print(f"Local access:   http://127.0.0.1:7860")
            print(f"Public access:  {self.tunnel.public_url}")
            print("\nShare this link with anyone on the internet:")
            print(f"  → {self.tunnel.public_url}")
            print("=" * 70 + "\n")

            app.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,  # ngrok handles sharing
                show_error=True,
                quiet=False,
            )

        except KeyboardInterrupt:
            self._signal_handler(None, None)

        except Exception as e:
            print(f"\n❌ Error starting server: {e}")
            ngrok.kill()
            sys.exit(1)