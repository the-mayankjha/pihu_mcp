import sys
import os
import json
import ssl
import base64
import html
import re
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

def render_callback_page(success, user_name='', user_email=''):
    resources = Path(__file__).resolve().parent
    template = (resources / 'google_oauth_page.html').read_text(encoding='utf-8')
    logo = base64.b64encode((resources / 'pihu-logo.png').read_bytes()).decode('ascii')
    values = {
        '__TITLE__': "You're connected." if success else "Connection incomplete.",
        '__MESSAGE__': 'Your Google account has been linked to PIHU.' if success else 'Google could not complete the connection. Return to PIHU and try linking your account again.',
        '__ACCOUNT_NAME__': html.escape(user_name),
        '__ACCOUNT_EMAIL__': html.escape(user_email),
        '__ACCOUNT_HIDDEN__': '' if success and (user_name or user_email) else 'hidden',
        '__RETURN__': 'You can close this tab and return to PIHU.' if success else 'You can close this tab. Your existing connections remain unchanged.',
        '__LOGO__': 'data:image/png;base64,' + logo,
    }
    # Substitute once so account text cannot introduce template tokens or HTML.
    return re.sub(r'__[A-Z_]+__', lambda match: values.get(match.group(), ''), template)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    client_id = ""
    client_secret = ""
    token_save_path = os.path.expanduser("~/.gemini/antigravity/google_workspace_tokens.json")

    def send_callback_page(self, status, success, user_name='', user_email=''):
        page = render_callback_page(success, user_name, user_email).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Length', str(len(page)))
        self.end_headers()
        self.wfile.write(page)

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
                        self.send_callback_page(500, False)
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

                    self.send_callback_page(200, True, user_name, user_email)

                    account_json = json.dumps({"email": user_email, "name": user_name, "picture": user_picture})
                    print(f"OAUTH_ACCOUNT_CONNECTED:{account_json}")
                    sys.stdout.flush()
                    sys.exit(0)
                else:
                    self.send_callback_page(400, False)
                    sys.exit(1)
            else:
                self.send_callback_page(400, False)
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
