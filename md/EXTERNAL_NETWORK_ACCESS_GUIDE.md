# 🌍 External Network Access Guide

## Accessing the App from Different Networks/Gateways

This guide explains how to access your Business Knowledge Assistant from devices on **different networks** (different gateways, internet, remote locations).

## 🚀 Quick Solution: Using ngrok (Recommended)

**ngrok** creates a secure tunnel to your local app, making it accessible from anywhere on the internet.

### Step 1: Install ngrok

1. **Download ngrok**: https://ngrok.com/download
2. **Extract** `ngrok.exe` to a folder (or add to PATH)
3. **Sign up** for a free account: https://dashboard.ngrok.com/signup

### Step 2: Configure ngrok

1. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
2. Run in Command Prompt:
   ```bash
   ngrok config add-authtoken YOUR_TOKEN_HERE
   ```

### Step 3: Run the App with ngrok

**Option A: Use the batch file (easiest)**
```bash
run_app_with_ngrok.bat
```

**Option B: Manual setup**
1. Start Streamlit:
   ```bash
   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
   ```
2. In another terminal, start ngrok:
   ```bash
   ngrok http 8501
   ```
3. Copy the HTTPS URL from ngrok (e.g., `https://abc123.ngrok-free.app`)
4. Share this URL with users on different networks

### Step 4: Access from Anywhere

- **From any device**: Open the ngrok URL in a web browser
- **From different networks**: Works from anywhere on the internet
- **No router configuration needed**: Works behind firewalls/NAT

### ngrok Features

✅ **Free tier available** (with limitations)
✅ **HTTPS by default** (secure connection)
✅ **No router configuration** needed
✅ **Works from anywhere** (internet, mobile, etc.)
✅ **Easy setup** (5 minutes)

### ngrok Limitations (Free Tier)

- **Session timeout**: Free tunnels expire after 2 hours
- **Random URLs**: Each restart gets a new URL
- **Rate limits**: Limited requests per minute
- **Warning page**: ngrok shows a warning page (can be dismissed)

### Upgrade ngrok (Optional)

For production use, consider ngrok paid plans:
- Static domains (same URL every time)
- No session timeouts
- Higher rate limits
- Custom domains

---

## 🔧 Alternative Solution: Router Port Forwarding

If you have router access and want a permanent solution:

### Step 1: Configure Router Port Forwarding

1. **Access your router** (usually `192.168.1.1` or `192.168.0.1`)
2. **Find Port Forwarding** settings (under "Advanced" or "NAT")
3. **Add a new rule**:
   - **External Port**: `8501` (or any port you prefer)
   - **Internal IP**: Your PC's local IP (find with `ipconfig`)
   - **Internal Port**: `8501`
   - **Protocol**: TCP
4. **Save** the configuration

### Step 2: Find Your Public IP

1. Visit: https://whatismyipaddress.com/
2. Note your **public IP address**
3. This IP may change (see Dynamic DNS below)

### Step 3: Configure Firewall

Allow incoming connections on port 8501:
```
Windows Security → Firewall → Advanced Settings → Inbound Rules
→ New Rule → Port → TCP → 8501 → Allow
```

### Step 4: Access from External Network

- **From any device**: `http://YOUR_PUBLIC_IP:8501`
- **Example**: `http://203.0.113.45:8501`

### Step 5: Use Dynamic DNS (Optional)

If your public IP changes frequently:

1. **Sign up for Dynamic DNS** service:
   - No-IP: https://www.noip.com/
   - DuckDNS: https://www.duckdns.org/
   - Dynu: https://www.dynu.com/

2. **Create a hostname** (e.g., `myapp.ddns.net`)

3. **Configure your router** or use a DDNS updater client

4. **Access via hostname**: `http://myapp.ddns.net:8501`

---

## 🔐 Security Considerations

⚠️ **IMPORTANT**: Exposing your app to the internet has security risks!

### Recommended Security Measures:

1. **Add Authentication**:
   - Streamlit supports password protection
   - Add to `.streamlit/config.toml`:
     ```toml
     [server]
     enableXsrfProtection = true
     ```

2. **Use HTTPS**:
   - ngrok provides HTTPS automatically
   - For port forwarding, use a reverse proxy (Nginx/Caddy) with SSL

3. **Restrict Access**:
   - Use firewall rules to limit access
   - Consider VPN for trusted users only

4. **Monitor Access**:
   - Check Streamlit logs regularly
   - Monitor for suspicious activity

5. **Keep Updated**:
   - Keep Streamlit and dependencies updated
   - Apply security patches promptly

---

## 📊 Comparison of Methods

| Method | Setup Difficulty | Cost | Security | Reliability |
|--------|------------------|------|----------|-------------|
| **ngrok** | ⭐ Easy | Free/Paid | HTTPS | High |
| **Port Forwarding** | ⭐⭐ Medium | Free | HTTP* | Medium |
| **VPN** | ⭐⭐⭐ Hard | Free/Paid | High | High |
| **Cloud Hosting** | ⭐⭐ Medium | Paid | High | Very High |

*Can add HTTPS with reverse proxy

---

## 🛠️ Troubleshooting

### ngrok Issues

**"ngrok not found"**
- Ensure ngrok.exe is in PATH or same folder
- Download from official site: https://ngrok.com/download

**"Tunnel session expired"**
- Free ngrok tunnels expire after 2 hours
- Restart ngrok to get a new URL
- Or upgrade to paid plan for persistent URLs

**"Connection refused"**
- Ensure Streamlit is running on port 8501
- Check firewall isn't blocking localhost:8501

### Port Forwarding Issues

**"Cannot connect from external network"**
1. Verify port forwarding rule is saved
2. Check firewall allows incoming connections
3. Verify your public IP hasn't changed
4. Test with: https://www.canyouseeme.org/ (port 8501)

**"IP address changed"**
- Use Dynamic DNS service (see above)
- Or check IP regularly and update users

**"Connection timeout"**
- Some ISPs block incoming connections
- Consider using ngrok instead
- Or contact ISP about port blocking

---

## 🎯 Quick Start Summary

### For Quick Testing (ngrok):
1. Install ngrok and configure authtoken
2. Run: `run_app_with_ngrok.bat`
3. Share the ngrok URL

### For Permanent Setup (Port Forwarding):
1. Configure router port forwarding (port 8501)
2. Set up firewall rules
3. Get public IP or use Dynamic DNS
4. Share URL: `http://YOUR_PUBLIC_IP:8501`

### Recommended for Most Users:
**Use ngrok** - It's the easiest and most reliable solution for accessing across different networks without router configuration.

---

## 📝 Additional Resources

- **ngrok Documentation**: https://ngrok.com/docs
- **Streamlit Deployment**: https://docs.streamlit.io/knowledge-base/deploy
- **Port Forwarding Guide**: https://portforward.com/router/
- **Dynamic DNS Services**: https://www.noip.com/ or https://www.duckdns.org/

