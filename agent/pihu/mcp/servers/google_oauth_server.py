import sys
import os
import json
import ssl
import subprocess
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    client_id = ""
    client_secret = ""
    token_save_path = os.path.expanduser("~/.gemini/antigravity/google_workspace_tokens.json")

    def fetch_user_info(self, access_token):
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Try urllib
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(userinfo_url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            # Fallback to curl
            try:
                curl_cmd = ["curl", "-s", "-H", f"Authorization: Bearer {access_token}", userinfo_url]
                res = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
                return json.loads(res.stdout)
            except Exception:
                return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/oauth2callback":
            query = urllib.parse.parse_qs(parsed.query)
            code = query.get("code", [None])[0]
            if code:
                token_url = "https://oauth2.googleapis.com/token"
                post_data = {
                    "code": code,
                    "client_id": OAuthCallbackHandler.client_id,
                    "client_secret": OAuthCallbackHandler.client_secret,
                    "redirect_uri": "http://localhost:8080/oauth2callback",
                    "grant_type": "authorization_code"
                }

                token_resp = None

                # Attempt 1: Standard urllib
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    encoded_data = urllib.parse.urlencode(post_data).encode("utf-8")
                    req = urllib.request.Request(
                        token_url,
                        data=encoded_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
                    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                        token_resp = json.loads(resp.read().decode("utf-8"))
                except Exception as e1:
                    print(f"urllib exchange failed ({e1}), trying curl fallback...", file=sys.stderr)
                    # Attempt 2: System curl fallback
                    try:
                        curl_cmd = [
                            "curl", "-s", "-X", "POST", token_url,
                            "-d", f"code={urllib.parse.quote(code)}",
                            "-d", f"client_id={urllib.parse.quote(OAuthCallbackHandler.client_id)}",
                            "-d", f"client_secret={urllib.parse.quote(OAuthCallbackHandler.client_secret)}",
                            "-d", "redirect_uri=http://localhost:8080/oauth2callback",
                            "-d", "grant_type=authorization_code"
                        ]
                        res = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
                        token_resp = json.loads(res.stdout)
                    except Exception as e2:
                        err_msg = f"OAuth Token Exchange failed: {str(e2)}"
                        print(err_msg, file=sys.stderr)
                        self.send_response(500)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(f"<h3>OAuth Exchange Error</h3><p>{err_msg}</p>".encode("utf-8"))
                        sys.exit(1)

                if token_resp and ("access_token" in token_resp or "refresh_token" in token_resp):
                    access_token = token_resp.get("access_token", "")
                    user_info = self.fetch_user_info(access_token) if access_token else {}

                    user_email = user_info.get("email", "connected.user@google.com")
                    user_name = user_info.get("name", user_email.split("@")[0].capitalize())
                    user_picture = user_info.get("picture", "")

                    # Read existing multi-account token storage if exists
                    existing_data = {}
                    if os.path.exists(OAuthCallbackHandler.token_save_path):
                        try:
                            with open(OAuthCallbackHandler.token_save_path, "r") as f:
                                existing_data = json.load(f)
                        except Exception:
                            existing_data = {}

                    accounts = existing_data.get("accounts", [])
                    # Remove any existing entry for this email to update it
                    accounts = [a for a in accounts if a.get("email", "").lower() != user_email.lower()]

                    account_entry = {
                        "email": user_email,
                        "name": user_name,
                        "picture": user_picture,
                        "access_token": token_resp.get("access_token"),
                        "refresh_token": token_resp.get("refresh_token", existing_data.get("refresh_token")),
                        "token_type": token_resp.get("token_type", "Bearer"),
                        "scope": token_resp.get("scope"),
                        "expires_in": token_resp.get("expires_in"),
                        "is_primary": len(accounts) == 0,
                        "connected_at": urllib.parse.quote(user_email)
                    }
                    accounts.append(account_entry)

                    full_token_storage = {
                        "client_id": OAuthCallbackHandler.client_id,
                        "client_secret": OAuthCallbackHandler.client_secret,
                        "access_token": token_resp.get("access_token"),
                        "refresh_token": token_resp.get("refresh_token", existing_data.get("refresh_token")),
                        "current_user": account_entry,
                        "accounts": accounts
                    }

                    os.makedirs(os.path.dirname(OAuthCallbackHandler.token_save_path), exist_ok=True)
                    with open(OAuthCallbackHandler.token_save_path, "w") as f:
                        json.dump(full_token_storage, f, indent=2)

                    avatar_html = f'<img src="{user_picture}" style="width: 64px; height: 64px; border-radius: 50%; margin: 0 auto 16px auto; border: 2px solid #ec4899;" />' if user_picture else f'<div style="width: 60px; height: 60px; background: linear-gradient(135deg, #ec4899, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; font-size: 26px; color: #fff; font-weight: bold;">{user_name[0].upper()}</div>'

                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>PIHU OS - Account Linked</title>
                        <meta charset="utf-8">
                    </head>
                    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f12; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
                        <div style="text-align: center; padding: 40px; background: #18181b; border: 1px solid #27272a; border-radius: 24px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); max-width: 440px;">
                            {avatar_html}
                            <h1 style="color: #ec4899; margin: 0 0 6px 0; font-size: 22px;">Account Linked Successfully!</h1>
                            <p style="color: #ffffff; font-size: 16px; font-weight: 600; margin: 0 0 4px 0;">{user_name}</p>
                            <p style="color: #a1a1aa; font-size: 14px; margin: 0 0 24px 0;">{user_email}</p>
                            <div style="padding: 12px; background: rgba(236, 72, 153, 0.1); border: 1px solid rgba(236, 72, 153, 0.3); border-radius: 12px; font-size: 13px; color: #f472b6; margin-bottom: 24px;">
                                Gmail, Calendar, Docs, Tasks, Keep & Drive Automation Active
                            </div>
                            <p style="color: #71717a; font-size: 12px; margin: 0;">You can close this tab and return to PIHU OS.</p>
                        </div>
                    </body>
                    </html>
                    """
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))

                    account_json = json.dumps({"email": user_email, "name": user_name, "picture": user_picture})
                    print(f"OAUTH_ACCOUNT_CONNECTED:{account_json}")
                    sys.stdout.flush()
                    sys.exit(0)
                else:
                    err_json = json.dumps(token_resp)
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f"<h3>Google OAuth Error</h3><pre>{err_json}</pre>".encode("utf-8"))
                    sys.exit(1)
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code parameter")
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    if len(sys.argv) > 2:
        OAuthCallbackHandler.client_id = sys.argv[1]
        OAuthCallbackHandler.client_secret = sys.argv[2]
    
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, OAuthCallbackHandler)
    print("OAUTH_SERVER_STARTED_PORT_8080")
    sys.stdout.flush()
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
