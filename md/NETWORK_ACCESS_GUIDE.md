# 🌐 Network Access Guide

## Accessing the App from Another PC

By default, Streamlit only accepts connections from localhost. To enable network access, you have two options:

## Option 1: Use the Network Startup Script (Recommended)

1. **Double-click `run_app_network.bat`** to start the app with network access enabled.

2. **Find your PC's IP address:**
   - Open Command Prompt or PowerShell
   - Run: `ipconfig`
   - Look for "IPv4 Address" under your active network adapter (usually "Wireless LAN adapter Wi-Fi" or "Ethernet adapter Ethernet")
   - Example: `192.168.1.100`

3. **Access from another PC:**
   - Open a web browser on the other PC
   - Navigate to: `http://YOUR_IP_ADDRESS:8501`
   - Example: `http://192.168.1.100:8501`

## Option 2: Use Streamlit Config File (Permanent)

The app is already configured to accept network connections via `.streamlit/config.toml`. Simply run:

```bash
streamlit run app.py
```

The app will automatically listen on all network interfaces (0.0.0.0).

## 🔒 Security Considerations

⚠️ **Important Security Notes:**

1. **Firewall**: Windows Firewall may block incoming connections. You may need to:
   - Allow Streamlit through Windows Firewall
   - Or temporarily disable firewall for testing (not recommended for production)

2. **Local Network Only**: This setup allows access from devices on the same local network. For internet access from different networks/gateways, see:
   - **`EXTERNAL_NETWORK_ACCESS_GUIDE.md`** - Complete guide for external access
   - **Quick solution**: Use ngrok (see `run_app_with_ngrok.bat`)
   - **Permanent solution**: Router port forwarding (see guide)

3. **No Authentication**: The app currently has no login/password protection. Anyone on your network can access it.

## 🛠️ Troubleshooting

### "Cannot connect" from another PC

1. **Check Windows Firewall:**
   ```
   Windows Security → Firewall & network protection → Allow an app through firewall
   ```
   Add Python or Streamlit to allowed apps.

2. **Verify IP Address:**
   - Make sure you're using the correct IP address from `ipconfig`
   - Ensure both PCs are on the same network (same Wi-Fi or same router)

3. **Check if Streamlit is running:**
   - Look at the terminal where you started the app
   - You should see: "You can now view your Streamlit app in your browser"
   - The URL should show `0.0.0.0:8501` or `Network URL: http://192.168.x.x:8501`

4. **Test connection locally first:**
   - Try accessing from the host PC using the IP address instead of localhost
   - Example: `http://192.168.1.100:8501` (from the same PC)

### "Connection refused" error

- Make sure the app is running on the host PC
- Verify the port 8501 is not blocked by firewall
- Check that no other application is using port 8501

## 📝 Quick Reference

**Start app with network access:**
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

**Or use the batch file:**
```bash
run_app_network.bat
```

**Find your IP address:**
```bash
ipconfig
```

**Access from another PC:**
```
http://YOUR_IP_ADDRESS:8501
```

