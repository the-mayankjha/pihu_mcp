package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// MCPTab represents the active view tab in the MCP Registry modal.
type MCPTab int

const (
	MCPTabConnected MCPTab = iota
	MCPTabCatalog
	MCPTabGuide
)

// ConnectedMCPServer represents a live active MCP server.
type ConnectedMCPServer struct {
	Name        string
	Transport   string
	ToolCount   int
	Status      string
	Description string
	Tools       []string
}

// CommunityMCPItem represents an MCP server available for installation from registry.
type CommunityMCPItem struct {
	ID            string
	DisplayName   string
	Category      string
	Description   string
	InstallCmd    string
	Prereqs       string
	EnvVars       []string
	ConfigSnippet string
	ToolsProvided []string
	GuideSteps    []string
}

var ActiveConnectedServers = []ConnectedMCPServer{
	{
		Name:        "pihu-file-mcp",
		Transport:   "stdio · python",
		ToolCount:   24,
		Status:      "● Online",
		Description: "Filesystem operations: read, write, grep, fuzzy search, directory trees, file patching & diffs.",
		Tools: []string{
			"read_file", "write_file", "edit_file", "replace_text", "tree", "search_files",
			"grep_search", "list_dir", "create_dir", "delete_file", "stat_file", "diff_file",
		},
	},
	{
		Name:        "pihu-system-mcp",
		Transport:   "stdio · python",
		ToolCount:   7,
		Status:      "● Online",
		Description: "Local system inspect, shell execution, memory usage, CPU, processes & native notifications.",
		Tools: []string{
			"get_system_info", "run_shell", "list_processes", "kill_process", "send_notification", "get_env", "disk_usage",
		},
	},
	{
		Name:        "pihu-web-search-mcp",
		Transport:   "stdio · python",
		ToolCount:   6,
		Status:      "● Online",
		Description: "Realtime web search, full web page scraper, markdown parser, download file & URL fetch.",
		Tools: []string{
			"web_search", "web_fetch", "web_search_and_read", "web_download_file", "extract_links", "fetch_metadata",
		},
	},
	{
		Name:        "google-workspace-mcp",
		Transport:   "stdio · python",
		ToolCount:   10,
		Status:      "● Online",
		Description: "Gmail send/search/draft, Google Calendar events, Google Drive search, Docs editor & Sheets.",
		Tools: []string{
			"gmail_search", "gmail_send", "gmail_draft", "calendar_list_events", "calendar_create_event",
			"drive_search_files", "drive_read_file", "docs_create", "sheets_read", "sheets_append",
		},
	},
	{
		Name:        "pihu-project-mcp",
		Transport:   "stdio · node",
		ToolCount:   6,
		Status:      "● Online",
		Description: "Project scaffolding, automated unit tests runner, build diagnostic fixer & server manager.",
		Tools: []string{
			"scaffold_project", "test_project", "diagnose_and_fix", "manage_server", "audit_dependencies", "bundle_assets",
		},
	},
}

var CommunityMCPCatalog = []CommunityMCPItem{
	{
		ID:          "sqlite",
		DisplayName: "SQLite Database MCP",
		Category:    "Database",
		Description: "Query, introspect, and execute SQL across local SQLite databases",
		InstallCmd:  "pip install mcp-server-sqlite",
		Prereqs:     "Python 3.10+ (pip)",
		EnvVars:     []string{"SQLITE_DB_PATH=/path/to/database.db"},
		ConfigSnippet: `{\n  "sqlite": {\n    "command": "python",\n    "args": ["-m", "mcp_server_sqlite", "--db-path", "./app.db"]\n  }\n}`,
		ToolsProvided: []string{"read_query", "write_query", "create_table", "list_tables", "describe_table"},
		GuideSteps: []string{
			"1. Install the SQLite MCP package: pip install mcp-server-sqlite",
			"2. Add server configuration to mcp/config.json",
			"3. Specify your SQLite database file path in args or env",
			"4. Restart PIHU or run /mcp to start querying SQLite databases natively",
		},
	},
	{
		ID:          "postgres",
		DisplayName: "PostgreSQL Database MCP",
		Category:    "Database",
		Description: "Connect and manage PostgreSQL schemas, queries, migrations and tables",
		InstallCmd:  "pip install mcp-server-postgres",
		Prereqs:     "PostgreSQL Database URI & Python 3.10+",
		EnvVars:     []string{"POSTGRES_URL=postgresql://user:pass@localhost:5432/dbname"},
		ConfigSnippet: `{\n  "postgres": {\n    "command": "python",\n    "args": ["-m", "mcp_server_postgres", "postgresql://user:pass@localhost:5432/dbname"]\n  }\n}`,
		ToolsProvided: []string{"query", "execute", "list_schemas", "list_tables", "describe_table"},
		GuideSteps: []string{
			"1. Install the Postgres MCP: pip install mcp-server-postgres",
			"2. Set POSTGRES_URL in your .env or pass as argument in mcp/config.json",
			"3. Launch PIHU: AI agent will be able to analyze table schemas and execute SQL",
		},
	},
	{
		ID:          "github",
		DisplayName: "GitHub Integration MCP",
		Category:    "Developer Tools",
		Description: "Create PRs, issues, read commits, workflows, and search code",
		InstallCmd:  "npx -y @modelcontextprotocol/server-github",
		Prereqs:     "Node.js 18+ and GitHub Personal Access Token (classic or fine-grained)",
		EnvVars:     []string{"GITHUB_PERSONAL_ACCESS_TOKEN=ghp_yourTokenHere"},
		ConfigSnippet: `{\n  "github": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-github"],\n    "env": {\n      "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxx"\n    }\n  }\n}`,
		ToolsProvided: []string{"create_issue", "create_pull_request", "get_file_contents", "search_repositories", "list_commits", "create_branch"},
		GuideSteps: []string{
			"1. Generate a GitHub Personal Access Token with 'repo' and 'workflow' permissions",
			"2. Export GITHUB_PERSONAL_ACCESS_TOKEN in .env or configure in mcp/config.json",
			"3. Run PIHU: Agent can directly inspect PRs, review code, and commit branches",
		},
	},
	{
		ID:          "docker",
		DisplayName: "Docker Engine MCP",
		Category:    "DevOps & Cloud",
		Description: "Inspect, start, stop containers, view container logs, and manage images",
		InstallCmd:  "pip install mcp-server-docker",
		Prereqs:     "Docker Desktop / Docker Daemon running locally",
		EnvVars:     []string{"DOCKER_HOST=unix:///var/run/docker.sock"},
		ConfigSnippet: `{\n  "docker": {\n    "command": "python",\n    "args": ["-m", "mcp_server_docker"]\n  }\n}`,
		ToolsProvided: []string{"list_containers", "start_container", "stop_container", "get_logs", "list_images", "build_image"},
		GuideSteps: []string{
			"1. Ensure Docker daemon or Docker Desktop is running",
			"2. Install Docker MCP: pip install mcp-server-docker",
			"3. Register in mcp/config.json to allow PIHU to monitor containers & dev servers",
		},
	},
	{
		ID:          "puppeteer",
		DisplayName: "Puppeteer Web Automation MCP",
		Category:    "Web & Scraping",
		Description: "Headless Chrome automation, full-page screenshots, and interactive DOM inspection",
		InstallCmd:  "npx -y @modelcontextprotocol/server-puppeteer",
		Prereqs:     "Node.js 18+ (bundled Chromium)",
		EnvVars:     nil,
		ConfigSnippet: `{\n  "puppeteer": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-puppeteer"]\n  }\n}`,
		ToolsProvided: []string{"navigate", "screenshot", "click", "fill", "evaluate_javascript", "hover"},
		GuideSteps: []string{
			"1. Run npx -y @modelcontextprotocol/server-puppeteer",
			"2. Add to mcp/config.json",
			"3. Agent can autonomously browse web pages, take screenshots, and test UI components",
		},
	},
	{
		ID:          "fetch",
		DisplayName: "Universal Fetch & Web Scraper MCP",
		Category:    "Web & Scraping",
		Description: "Fetch and convert web pages into clean LLM-friendly markdown",
		InstallCmd:  "pip install mcp-server-fetch",
		Prereqs:     "Python 3.10+",
		EnvVars:     nil,
		ConfigSnippet: `{\n  "fetch": {\n    "command": "python",\n    "args": ["-m", "mcp_server_fetch"]\n  }\n}`,
		ToolsProvided: []string{"fetch_url", "fetch_markdown", "extract_text", "extract_html"},
		GuideSteps: []string{
			"1. Install fetch MCP: pip install mcp-server-fetch",
			"2. Add fetch server to mcp/config.json",
			"3. Use PIHU to ingest web articles, documentation, and live APIs",
		},
	},
	{
		ID:          "brave-search",
		DisplayName: "Brave Web Search API MCP",
		Category:    "Search",
		Description: "Privacy-focused real-time web search and index querying",
		InstallCmd:  "npx -y @modelcontextprotocol/server-brave-search",
		Prereqs:     "Brave Search API Key (Free tier at https://brave.com/search/api)",
		EnvVars:     []string{"BRAVE_API_KEY=BSA_yourBraveApiKey"},
		ConfigSnippet: `{\n  "brave-search": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-brave-search"],\n    "env": {\n      "BRAVE_API_KEY": "BSA_xxxxxxxxx"\n    }\n  }\n}`,
		ToolsProvided: []string{"brave_web_search", "brave_local_search"},
		GuideSteps: []string{
			"1. Obtain a free API key at https://brave.com/search/api/",
			"2. Add BRAVE_API_KEY to .env",
			"3. Register brave-search in mcp/config.json for fast search indexing",
		},
	},
	{
		ID:          "slack",
		DisplayName: "Slack Workspace MCP",
		Category:    "Productivity",
		Description: "Read channels, send messages, threads, and workspace notifications",
		InstallCmd:  "npx -y @modelcontextprotocol/server-slack",
		Prereqs:     "Slack Bot Token (xoxb-...) and App Token (xapp-...)",
		EnvVars:     []string{"SLACK_BOT_TOKEN=xoxb-...", "SLACK_TEAM_ID=T0..."},
		ConfigSnippet: `{\n  "slack": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-slack"],\n    "env": {\n      "SLACK_BOT_TOKEN": "xoxb-xxxx",\n      "SLACK_TEAM_ID": "T0xxxx"\n    }\n  }\n}`,
		ToolsProvided: []string{"list_channels", "post_message", "reply_to_thread", "add_reaction", "get_channel_history"},
		GuideSteps: []string{
			"1. Create a Slack App in your workspace at https://api.slack.com/apps",
			"2. Add 'chat:write' and 'channels:read' OAuth scopes",
			"3. Set SLACK_BOT_TOKEN and add to mcp/config.json",
		},
	},
	{
		ID:          "redis",
		DisplayName: "Redis Cache & Key-Value MCP",
		Category:    "Database",
		Description: "Introspect keys, execute Redis commands, monitor pub/sub and memory stats",
		InstallCmd:  "pip install mcp-server-redis",
		Prereqs:     "Redis server running (local or cloud)",
		EnvVars:     []string{"REDIS_URL=redis://localhost:6379"},
		ConfigSnippet: `{\n  "redis": {\n    "command": "python",\n    "args": ["-m", "mcp_server_redis", "--url", "redis://localhost:6379"]\n  }\n}`,
		ToolsProvided: []string{"get_key", "set_key", "delete_key", "list_keys", "redis_info"},
		GuideSteps: []string{
			"1. Install Redis MCP: pip install mcp-server-redis",
			"2. Configure REDIS_URL in mcp/config.json",
			"3. Agent can directly verify caches, session keys, and database performance",
		},
	},
	{
		ID:          "notion",
		DisplayName: "Notion Workspace MCP",
		Category:    "Productivity",
		Description: "Read and create Notion pages, query databases, append blocks and sync notes",
		InstallCmd:  "npx -y @modelcontextprotocol/server-notion",
		Prereqs:     "Notion Internal Integration Token (secret_...)",
		EnvVars:     []string{"NOTION_API_KEY=secret_yourNotionToken"},
		ConfigSnippet: `{\n  "notion": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-notion"],\n    "env": {\n      "NOTION_API_KEY": "secret_xxxxxx"\n    }\n  }\n}`,
		ToolsProvided: []string{"search_pages", "read_page", "create_page", "query_database", "append_block_children"},
		GuideSteps: []string{
			"1. Create an integration at https://www.notion.so/my-integrations",
			"2. Share desired Notion pages/databases with the integration",
			"3. Configure NOTION_API_KEY in mcp/config.json",
		},
	},
}

// RenderMCPRegistryModal renders the unified MCP Registry with Connected Servers, Community Catalog, and Detailed Guide.
func RenderMCPRegistryModal(
	activeTab MCPTab,
	connected []ConnectedMCPServer,
	catalog []CommunityMCPItem,
	selectedConnectedIdx int,
	selectedCatalogIdx int,
	w, h int,
) string {
	modalW := min(84, w-6)
	if modalW < 40 {
		modalW = 40
	}
	innerW := modalW - 4

	var rows []string

	// Header & Title
	title := lipgloss.NewStyle().Foreground(colMauve).Bold(true).
		Render("◇ PIHU MCP Registry & Server Manager")

	// Tabs bar
	tabConnectedStyle := lipgloss.NewStyle().Foreground(colMuted)
	tabCatalogStyle := lipgloss.NewStyle().Foreground(colMuted)
	tabGuideStyle := lipgloss.NewStyle().Foreground(colMuted)

	if activeTab == MCPTabConnected {
		tabConnectedStyle = lipgloss.NewStyle().Foreground(colGreen).Bold(true)
	} else if activeTab == MCPTabCatalog {
		tabCatalogStyle = lipgloss.NewStyle().Foreground(colSky).Bold(true)
	} else if activeTab == MCPTabGuide {
		tabGuideStyle = lipgloss.NewStyle().Foreground(colYellow).Bold(true)
	}

	tabBar := fmt.Sprintf("[%s]   [%s]   [%s]",
		tabConnectedStyle.Render(fmt.Sprintf("1. Connected Servers (%d)", len(connected))),
		tabCatalogStyle.Render(fmt.Sprintf("2. Installable Catalog (%d)", len(catalog))),
		tabGuideStyle.Render("3. Setup Guide"),
	)

	navHint := lipgloss.NewStyle().Foreground(colSubtext).
		Render("Tab/1/2/3: Switch View  ·  Enter: View Guide & Setup  ·  Esc: Close")

	divider := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW))

	rows = append(rows, title, tabBar, navHint, divider)

	// Tab 1: Connected Servers
	if activeTab == MCPTabConnected {
		rows = append(rows, lipgloss.NewStyle().Foreground(colGreen).Bold(true).
			Render("● Active MCP Servers in Local Runtime (53 tools ready):"), "")

		for i, srv := range connected {
			isSelected := (i == selectedConnectedIdx)
			pointer := "  "
			nameStyle := lipgloss.NewStyle().Foreground(colSky).Bold(true)
			statusStyle := lipgloss.NewStyle().Foreground(colGreen).Bold(true)
			descStyle := lipgloss.NewStyle().Foreground(colSubtext)

			if isSelected {
				pointer = lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("❯ ")
				nameStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
				descStyle = lipgloss.NewStyle().Foreground(colText)
			}

			top := fmt.Sprintf("%s%s  %s  %s",
				pointer,
				nameStyle.Render(srv.Name),
				statusStyle.Render(srv.Status),
				lipgloss.NewStyle().Foreground(colMuted).Render("("+srv.Transport+" · "+fmt.Sprintf("%d tools", srv.ToolCount)+")"),
			)
			desc := "    " + descStyle.Render(srv.Description)
			toolsSample := "    " + lipgloss.NewStyle().Foreground(colMuted).Italic(true).
				Render("Tools: "+strings.Join(srv.Tools[:min(6, len(srv.Tools))], " · ") + " ...")

			rows = append(rows, top, desc, toolsSample, "")
		}
	} else if activeTab == MCPTabCatalog {
		// Tab 2: Community Catalog
		rows = append(rows, lipgloss.NewStyle().Foreground(colSky).Bold(true).
			Render("◇ Community MCP Catalog — Select any server and press Enter for Setup Guide:"), "")

		maxShow := 5
		start := 0
		if selectedCatalogIdx >= maxShow {
			start = selectedCatalogIdx - maxShow + 1
		}
		end := min(len(catalog), start+maxShow)

		for i := start; i < end; i++ {
			item := catalog[i]
			isSelected := (i == selectedCatalogIdx)

			pointer := "  "
			nameStyle := lipgloss.NewStyle().Foreground(colSky).Bold(true)
			catStyle := lipgloss.NewStyle().Foreground(colMuted)
			descStyle := lipgloss.NewStyle().Foreground(colSubtext)

			if isSelected {
				pointer = lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("❯ ")
				nameStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
				descStyle = lipgloss.NewStyle().Foreground(colText)
			}

			top := fmt.Sprintf("%s%s  %s",
				pointer,
				nameStyle.Render(item.DisplayName),
				catStyle.Render("["+item.Category+"]"),
			)
			desc := "    " + descStyle.Render(item.Description)
			install := "    " + lipgloss.NewStyle().Foreground(colYellow).Render("Install: "+item.InstallCmd)

			rows = append(rows, top, desc, install, "")
		}
	} else if activeTab == MCPTabGuide {
		// Tab 3: Detailed Installation & Setup Guide
		if selectedCatalogIdx >= 0 && selectedCatalogIdx < len(catalog) {
			item := catalog[selectedCatalogIdx]
			rows = append(rows,
				lipgloss.NewStyle().Foreground(colYellow).Bold(true).
					Render(fmt.Sprintf("◇ Setup & Integration Guide: %s (%s)", item.DisplayName, item.Category)),
				"",
				lipgloss.NewStyle().Foreground(colSky).Bold(true).Render("1. Install Command:"),
				"   " + lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render(item.InstallCmd),
				"",
				lipgloss.NewStyle().Foreground(colSky).Bold(true).Render("2. Prerequisites:"),
				"   " + lipgloss.NewStyle().Foreground(colText).Render(item.Prereqs),
				"",
			)

			if len(item.EnvVars) > 0 {
				rows = append(rows,
					lipgloss.NewStyle().Foreground(colSky).Bold(true).Render("3. Required Environment Variables (.env):"),
				)
				for _, ev := range item.EnvVars {
					rows = append(rows, "   "+lipgloss.NewStyle().Foreground(colPeach).Render(ev))
				}
				rows = append(rows, "")
			}

			rows = append(rows,
				lipgloss.NewStyle().Foreground(colSky).Bold(true).Render("4. Configuration Snippet (add to mcp/config.json):"),
				"   " + lipgloss.NewStyle().Foreground(colMauve).Render(item.ConfigSnippet),
				"",
				lipgloss.NewStyle().Foreground(colSky).Bold(true).Render("5. Tools Provided to AI Agent:"),
				"   " + lipgloss.NewStyle().Foreground(colSubtext).Render(strings.Join(item.ToolsProvided, " · ")),
				"",
				lipgloss.NewStyle().Foreground(colMuted).Render("Press Tab/1/2 to return to Catalog · Esc to close"),
			)
		}
	}

	return lipgloss.NewStyle().
		Width(modalW).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colGreen).
		Padding(1, 2).
		Render(strings.Join(rows, "\n"))
}
