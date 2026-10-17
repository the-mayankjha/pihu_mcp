#!/usr/bin/env python3
"""Publish completed GitHub release metadata to the authenticated pihu_web API."""
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=Path('manifest.json'))
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--api', default='https://pihu.nfks.co.in/api/v2')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    artifacts = [json.loads(path.read_text()) for path in sorted(args.artifacts.glob('*-*.json')) if path.name != 'release-manifest.json']
    targets = {(artifact['platform'], artifact['architecture']) for artifact in artifacts}
    required = {('macos','arm64'), ('macos','x64'), ('windows','x64'), ('linux','x64')}
    if targets != required or len(artifacts) != len(required): raise ValueError('The four platform artifacts must all be present exactly once')
    manifest['artifacts'] = artifacts
    (args.artifacts / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if args.prepare_only: raise SystemExit(0)
    token = os.environ.get('MARKET_PUBLISH_TOKEN')
    if not token:
        print('Official package manifest is hosted in the release; pihu_web discovers it through the trusted catalog.')
        raise SystemExit(0)
    notes = Path('RELEASE_NOTES.md').read_text() if Path('RELEASE_NOTES.md').is_file() else f'{manifest["display_name"]} {manifest["version"]}'
    request = urllib.request.Request(args.api.rstrip('/') + '/publisher/packages',
        data=json.dumps({'manifest':manifest, 'release_notes':notes}).encode(),
        headers={'Authorization':f'Bearer {token}', 'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            print(response.read().decode())
    except urllib.error.HTTPError as error:
        # Do not dump headers, tokens, or arbitrary remote response bodies.
        raise SystemExit(f'Market publication failed with HTTP {error.code}')
