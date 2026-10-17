"""PIHU Market client. Package metadata is resolved exclusively through pihu_web."""
import asyncio
import json
import os
import urllib.parse
import urllib.request
from pihu.mcp.manifest import MCPPackageManifest

DEFAULT_REGISTRY_URL = os.getenv('PIHU_MARKET_REGISTRY_URL', 'https://pihu.nfks.co.in/api/v2')

class MCPRegistryClient:
    def __init__(self, base_url=DEFAULT_REGISTRY_URL, timeout=20.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _request(self, path):
        request = urllib.request.Request(self.base_url + path, headers={'User-Agent': 'PIHU-Market/3', 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read(4 * 1024 * 1024 + 1)
                if len(payload) > 4 * 1024 * 1024: raise ValueError('Market response exceeds size limit')
                data = json.loads(payload)
                if not isinstance(data, dict): raise ValueError('Invalid Market API response')
                return data
        except Exception as error:
            raise ValueError(f'PIHU Market request failed: {error}') from error

    async def search(self, query='', category=None):
        params = {'type': 'mcp', 'q': query, 'limit': 100}
        if category: params['category'] = category
        data = await asyncio.to_thread(self._request, '/catalog?' + urllib.parse.urlencode(params))
        return data.get('packages', [])

    async def get_package_info(self, mcp_id):
        return await asyncio.to_thread(self._request, '/packages/' + urllib.parse.quote(mcp_id, safe=''))

    async def fetch_manifest(self, mcp_id, version='latest'):
        path = '/packages/' + urllib.parse.quote(mcp_id, safe='') + '/manifest'
        if version not in ('latest', '*'):
            path += '?' + urllib.parse.urlencode({'version': version})
        data = await asyncio.to_thread(self._request, path)
        payload = data.get('manifest', data)
        if not isinstance(payload, dict) or payload.get('type', 'mcp') != 'mcp':
            raise ValueError('Market API returned an invalid MCP manifest')
        return MCPPackageManifest.from_dict(payload)
