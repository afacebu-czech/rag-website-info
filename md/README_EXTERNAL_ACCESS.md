# 🌍 Quick Start: External Network Access

## Access from Different Networks/Gateways

To access your Business Knowledge Assistant from devices on **different networks** (different gateways, internet, remote locations):

### 🚀 Easiest Method: ngrok (Recommended)

1. **Install ngrok**:
   - Download: https://ngrok.com/download
   - Extract `ngrok.exe` to this folder or add to PATH

2. **Configure ngrok**:
   - Sign up: https://dashboard.ngrok.com/signup (free)
   - Get authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
   - Run: `ngrok config add-authtoken YOUR_TOKEN`

3. **Run the app**:
   ```bash
   run_app_with_ngrok.bat
   ```

4. **Share the ngrok URL** (e.g., `https://abc123.ngrok-free.app`) with users

✅ **Works from anywhere** - No router configuration needed!

---

### 📚 Full Documentation

- **`EXTERNAL_NETWORK_ACCESS_GUIDE.md`** - Complete guide with all options
- **`NETWORK_ACCESS_GUIDE.md`** - Local network access guide

---

### 🔧 Alternative Methods

- **Router Port Forwarding**: Permanent solution (requires router access)
- **VPN**: Secure but requires VPN server setup
- **Cloud Hosting**: Deploy to cloud services

See `EXTERNAL_NETWORK_ACCESS_GUIDE.md` for detailed instructions.

