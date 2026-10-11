"""Local desktop callback for the PIHU-hosted Google OAuth broker."""
import base64
import html
import json
import os
import re
import secrets
import ssl
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BROKER = os.environ.get("PIHU_OAUTH_BROKER", "https://pihu.nfks.co.in/api/v2/oauth/google")
TOKEN_PATH = Path.home() / ".gemini/antigravity/google_workspace_tokens.json"
GOOGLE_SCOPES = [
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/tasks",
]


def local_credentials():
    """Read an optional user-provided OAuth client for the offline broker fallback."""
    candidates = [
        Path.home() / ".gworkspace-mcp/credentials.json",
        Path.home() / ".config/google-workspace-mcp/credentials.json",
        Path.home() / ".pihu-os/config.json",
        TOKEN_PATH,
    ]
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sections = [data, data.get("installed", {}), data.get("web", {}), data.get("google_oauth", {})]
        for item in sections:
            if not isinstance(item, dict):
                continue
            client_id = item.get("client_id")
            client_secret = item.get("client_secret")
            if (isinstance(client_id, str) and client_id.endswith(".apps.googleusercontent.com")
                    and isinstance(client_secret, str) and client_secret
                    and not client_secret.startswith("${")):
                return client_id, client_secret
    raise RuntimeError(
        "The PIHU sign-in service is unavailable (HTTP 503), and no local Google OAuth client is configured. "
        "Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET with `pihu setup`, then retry."
    )


def exchange_local_code(code, client_id, client_secret, callback):
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": callback,
        "grant_type": "authorization_code",
    }).encode("ascii")
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def render_callback_page(success, user_name="", user_email=""):
    resources = Path(__file__).resolve().parent
    template = (resources / "google_oauth_page.html").read_text(encoding="utf-8")
    logo = base64.b64encode((resources / "pihu-logo.png").read_bytes()).decode("ascii")
    values = {
        "__TITLE__": "You're connected." if success else "Connection incomplete.",
        "__EYEBROW__": "Connecting to Google" if success else "Google Workspace sign-in",
        "__MESSAGE__": "Your Google account is linked. PIHU is ready to use your Google Workspace tools." if success else "Google could not complete the connection. Return to PIHU and try linking your account again.",
        "__ACCOUNT_NAME__": html.escape(user_name),
        "__ACCOUNT_EMAIL__": html.escape(user_email),
        "__ACCOUNT_HIDDEN__": "" if success and (user_name or user_email) else "hidden",
        "__STEPS_HIDDEN__": "" if success else "hidden",
        "__PRIVACY_HIDDEN__": "" if success else "hidden",
        "__APP_HIDDEN__": "" if success else "hidden",
        "__HINT_HIDDEN__": "" if success else "hidden",
        "__ERROR_HIDDEN__": "hidden" if success else "",
        "__ERROR__": "Google sign-in could not be completed. Return to PIHU and try again.",
        "__LOGO__": "data:image/png;base64," + logo,
    }
    return re.sub(r"__[A-Z_]+__", lambda match: values.get(match.group(), ""), template)


def request_json(url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def save_account(tokens):
    access_token = tokens.get("access_token")
    if not access_token:
        raise RuntimeError("PIHU did not return a Google access token.")
    req = urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=10) as response:
        user = json.loads(response.read().decode("utf-8"))
    email = user.get("email")
    if not email:
        raise RuntimeError("Google did not return the signed-in account email.")
    display_name = user.get("name") or email.split("@")[0]
    existing = {}
    try:
        existing = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    accounts = [item for item in existing.get("accounts", []) if item.get("email", "").lower() != email.lower()]
    account = {
        "email": email, "name": display_name, "picture": user.get("picture", ""),
        "access_token": access_token, "refresh_token": tokens.get("refresh_token") or existing.get("refresh_token"),
        "token_type": tokens.get("token_type", "Bearer"), "scope": tokens.get("scope"),
        "expires_in": tokens.get("expires_in"), "is_primary": not accounts, "connected_at": email,
    }
    accounts.append(account)
    data = {"access_token": access_token, "refresh_token": account["refresh_token"], "current_user": account, "accounts": accounts}
    if tokens.get("client_id") and tokens.get("client_secret"):
        data["client_id"] = tokens["client_id"]
        data["client_secret"] = tokens["client_secret"]
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    TOKEN_PATH.chmod(0o600)
    return account


class Callback(HTTPServer):
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    expected_state = ""
    callback_result = None
    broker_url = BROKER
    local_client = None
    callback_url = ""

    def log_message(self, *_args):
        return

    def respond_page(self, success, name="", email=""):
        page = render_callback_page(success, name, email).encode("utf-8")
        self.send_response(200 if success else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/oauth2callback" or not secrets.compare_digest(query.get("state", [""])[0], self.expected_state):
            self.respond_page(False)
            return
        if query.get("error"):
            Handler.callback_result = {"error": query["error"][0]}
            self.respond_page(False)
            return
        code, broker_state = query.get("code", [""])[0], query.get("broker_state", [""])[0]
        if not code:
            Handler.callback_result = {"error": "The PIHU OAuth callback was incomplete."}
            self.respond_page(False)
            return
        try:
            if broker_state:
                tokens = request_json(f"{Handler.broker_url}/exchange", {"code": code, "broker_state": broker_state})
            elif Handler.local_client:
                tokens = exchange_local_code(code, *Handler.local_client, Handler.callback_url)
                tokens["client_id"], tokens["client_secret"] = Handler.local_client
            else:
                raise RuntimeError("No OAuth exchange method is available.")
            account = save_account(tokens)
            Handler.callback_result = {"account": {"name": account["name"], "email": account["email"], "picture": account["picture"]}}
            # Only redirect to the hosted completion view after the callback
            # has exchanged tokens and persisted the account on this device.
            self.send_response(303)
            self.send_header("Location", "https://pihu.nfks.co.in/mcp/google/auth?status=connected")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
        except Exception as error:
            Handler.callback_result = {"error": str(error)}
            self.respond_page(False)


def run_server():
    Handler.expected_state = secrets.token_urlsafe(32)
    Handler.callback_result = None
    server = Callback(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    callback = f"http://127.0.0.1:{port}/oauth2callback"
    Handler.callback_url = callback
    Handler.broker_url = BROKER
    query = urllib.parse.urlencode({"callback": callback, "state": Handler.expected_state})
    provider = "pihu"
    try:
        auth = request_json(f"{BROKER}/start?{query}")
        if not isinstance(auth.get("auth_url"), str) or not auth["auth_url"].startswith("https://accounts.google.com/"):
            raise RuntimeError(auth.get("error", "PIHU did not return a Google sign-in URL."))
    except Exception as error:
        try:
            Handler.local_client = local_credentials()
            provider = "local"
            local_query = urllib.parse.urlencode({
                "client_id": Handler.local_client[0],
                "redirect_uri": callback,
                "response_type": "code",
                "scope": " ".join(GOOGLE_SCOPES),
                "access_type": "offline",
                "prompt": "consent",
                "state": Handler.expected_state,
            })
            auth = {"auth_url": "https://accounts.google.com/o/oauth2/v2/auth?" + local_query}
        except Exception as fallback_error:
            server.server_close()
            print(json.dumps({"error": str(fallback_error), "hosted_error": str(error)}), flush=True)
            raise SystemExit(1)
    auth_page = os.environ.get("PIHU_OAUTH_AUTH_PAGE", "https://pihu.nfks.co.in/mcp/google/auth")
    page_query = urllib.parse.urlencode({
        "callback": callback,
        "state": Handler.expected_state,
        "auth_url": auth["auth_url"],
    })
    print(json.dumps({
        "auth_url": auth["auth_url"],
        "auth_page_url": f"{auth_page}?{page_query}",
        "callback": callback,
        "state": Handler.expected_state,
        "port": port,
        "provider": provider,
    }), flush=True)
    server.timeout = 1
    import time
    deadline = time.monotonic() + 300
    while Handler.callback_result is None and time.monotonic() < deadline:
        server.handle_request()
    server.server_close()
    if Handler.callback_result and "account" in Handler.callback_result:
        print("OAUTH_ACCOUNT_CONNECTED:" + json.dumps(Handler.callback_result["account"]), flush=True)
    elif Handler.callback_result:
        print("OAUTH_ACCOUNT_ERROR:" + Handler.callback_result.get("error", "Sign-in failed"), flush=True)


if __name__ == "__main__":
    run_server()
