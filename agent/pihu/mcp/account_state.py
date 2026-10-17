"""Report account setup without exposing credential values or claiming token validity."""
import json
from pathlib import Path


def account_state(record):
    if not record.get('manifest', {}).get('auth_required'):
        return 'not_required'
    package_id = record.get('id')
    home = Path.home()
    if package_id == 'google-workspace-mcp':
        location = home / '.gemini/antigravity/google_workspace_tokens.json'
    elif package_id == 'spotify-mcp':
        location = home / '.config/pihu-os/spotify/config.json'
    elif package_id == 'pihu-whatsapp-mcp':
        # A durable device database does not prove the live session is connected.
        return 'saved_device' if (home / '.pihu/whatsapp/whatsapp.db').is_file() else 'pairing_required'
    else:
        return 'setup_required'
    try:
        data = json.loads(location.read_text())
        current = data.get('current_user', {}) if isinstance(data, dict) else {}
        tokens = data.get('tokens', {}) if isinstance(data, dict) else {}
        saved = any(value for value in [data.get('access_token'), data.get('refresh_token'), data.get('accessToken'), data.get('refreshToken'), current.get('access_token'), current.get('refresh_token'), tokens.get('access_token'), tokens.get('refresh_token')])
        return 'credentials_saved' if saved else 'sign_in_required'
    except (OSError, ValueError, AttributeError):
        return 'sign_in_required'
