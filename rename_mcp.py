import os

old_path = "mcp/servers/web-search-mcp"
new_path = "mcp/servers/pihu-web-search-mcp"

if os.path.exists(old_path):
    if os.path.exists(new_path):
        print("Target already exists")
    else:
        os.rename(old_path, new_path)
        print("Successfully renamed web-search-mcp to pihu-web-search-mcp")
else:
    print("old_path does not exist")
