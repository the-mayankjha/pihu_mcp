"""CLI bridge for installing and invoking real registry MCP packages."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from pihu.mcp.installer import MCPInstaller
from pihu.mcp.manager import MCPManager, resolve_mcp_config_path


async def _install(package_spec: str) -> int:
    success, message, _ = await MCPInstaller().install(package_spec, callback=lambda line: print("PIHU_MARKET_PROGRESS:" + json.dumps({"packageId": package_spec.split("@")[0], "message": line}), flush=True))
    print(message, file=sys.stdout if success else sys.stderr, flush=True)
    return 0 if success else 1


async def _remove(package_id: str) -> int:
    success, message = await MCPInstaller().uninstall(package_id)
    print(message, file=sys.stdout if success else sys.stderr, flush=True)
    return 0 if success else 1


def _default_servers() -> dict:
    try:
        payload = json.loads(resolve_mcp_config_path().read_text(encoding="utf-8"))
        servers = payload.get("servers", {})
        return servers if isinstance(servers, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


async def _list(as_json: bool) -> int:
    store = MCPInstaller().package_store
    records = store.list("mcp")
    defaults = _default_servers()
    installed_by_id = {item.get("id"): item for item in records if item.get("id")}
    for server_id, server in defaults.items():
        installed_by_id.setdefault(server_id, {"id": server_id, "name": server_id, "enabled": True, "bundled": True})
    items = list(installed_by_id.values())
    if as_json:
        print(json.dumps([public_record(item) for item in items], ensure_ascii=False))
    elif not items:
        print("No MCP packages are installed.")
    else:
        for item in items:
            state = "built-in" if item.get("bundled") else ("enabled" if item.get("enabled", True) else "disabled")
            print(f"{item.get('id')}\t{state}\t{item.get('version', '')}\t{item.get('display_name', item.get('name', ''))}")
    return 0


async def _tools(as_json: bool) -> int:
    manager = MCPManager()
    tools = []
    try:
        await manager.load_and_initialize()
        installed_ids = {record.get("id") for record in MCPInstaller().package_store.list("mcp") if record.get("enabled", True)}
        installed_ids.update(_default_servers().keys())
        definitions = {definition.name: definition for definition in manager.tools}
        for qualified_name, (server_id, tool_name) in manager.tool_map.items():
            if server_id not in installed_ids or "__" not in qualified_name:
                continue
            definition = definitions.get(tool_name)
            if not definition:
                continue
            tools.append({
                "server": server_id,
                "name": tool_name,
                "description": definition.description,
                "inputSchema": definition.parameters or {"type": "OBJECT", "properties": {}},
            })
    finally:
        await manager.close_all()
    if as_json:
        print(json.dumps(tools, ensure_ascii=False))
    else:
        for item in tools:
            print(f"{item['server']}\t{item['name']}\t{item['description']}")
    return 0


async def _call(server_id: str, tool_name: str, arguments: str) -> int:
    try:
        args = json.loads(arguments)
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object.")
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Invalid tool arguments: {error}", file=sys.stderr)
        return 2
    manager = MCPManager()
    try:
        await manager.load_and_initialize()
        key = f"{server_id}__{tool_name}"
        result = await manager.execute_tool(key, args)
        print(result)
        return 0
    except Exception as error:
        print(f"MCP tool call failed: {error}", file=sys.stderr)
        return 1
    finally:
        await manager.close_all()


def public_record(record):
    fields = ('id','name','display_name','description','version','runtime','transport','enabled','bundled','status','tools','missing_configuration','last_error','last_checked_at','installed_at')
    result = {key:record[key] for key in fields if key in record}
    from pihu.mcp.account_state import account_state
    result['account_state'] = account_state(record)
    result['required_configuration'] = record.get('manifest', {}).get('permissions', {}).get('env_vars_required', [])
    result['previous_version'] = (record.get('previous') or {}).get('version')
    return result

async def manage(action, package_id, configuration='{}'):
    installer = MCPInstaller()
    if action == 'diagnose': result = await installer.diagnose(package_id)
    elif action == 'rollback': result = installer.rollback(package_id)
    elif action == 'enable': result = installer.configure(package_id, enabled=True)
    elif action == 'disable': result = installer.configure(package_id, enabled=False)
    else:
        changes = json.loads(configuration)
        if not isinstance(changes, dict): raise ValueError('Configuration must be an object')
        records = {record['id']:record for record in installer.package_store.list('mcp')}
        result = installer.configure(package_id, env={**records[package_id].get('env',{}), **changes}, enabled=True)
    print(json.dumps(public_record(result)))
    return 0

def locate_asset(package_id, asset):
    import re
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,63}', package_id): raise ValueError('Invalid package ID')
    installer = MCPInstaller()
    record = next((item for item in installer.package_store.list('mcp') if item.get('id') == package_id), None)
    if not record: raise ValueError(f'Install {package_id} from the MCP Market first')
    if not record.get('enabled', True): raise ValueError(f'Enable {package_id} in the MCP Market first')
    root = Path(record['install_path']).resolve()
    expected = (installer.servers_dir / package_id / 'versions').resolve()
    if not root.is_relative_to(expected): raise ValueError('Invalid installed package location; reinstall this MCP')
    file = (root / asset).resolve()
    if not file.is_relative_to(root) or not file.is_file(): raise ValueError(f'{package_id} is missing {asset}; repair it in the MCP Market')
    print(json.dumps({'path':str(file),'version':record.get('version')}))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="pihu mcp")
    subparsers = parser.add_subparsers(dest="command", required=True)
    locate_parser = subparsers.add_parser("locate")
    locate_parser.add_argument("package_id")
    locate_parser.add_argument("asset")
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("package_spec")
    remove_parser = subparsers.add_parser("remove")
    remove_parser.add_argument("package_id")
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--json", action="store_true")
    tools_parser = subparsers.add_parser("tools")
    tools_parser.add_argument("--json", action="store_true")
    call_parser = subparsers.add_parser("call")
    call_parser.add_argument("server_id")
    call_parser.add_argument("tool_name")
    call_parser.add_argument("arguments", nargs="?", default="{}")
    for action in ('diagnose','rollback','enable','disable','configure'):
        operation = subparsers.add_parser(action)
        operation.add_argument('package_id')
        if action == 'configure': operation.add_argument('configuration')
    args = parser.parse_args()
    if args.command == "locate":
        code = locate_asset(args.package_id, args.asset)
    elif args.command == "install":
        code = asyncio.run(_install(args.package_spec))
    elif args.command == "remove":
        code = asyncio.run(_remove(args.package_id))
    elif args.command == "list":
        code = asyncio.run(_list(args.json))
    elif args.command == "tools":
        code = asyncio.run(_tools(args.json))
    elif args.command in ('diagnose','rollback','enable','disable','configure'):
        code = asyncio.run(manage(args.command, args.package_id, getattr(args, 'configuration', '{}')))
    else:
        code = asyncio.run(_call(args.server_id, args.tool_name, args.arguments))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
