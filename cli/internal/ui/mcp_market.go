package ui

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

// MCPTab represents the active view tab in the MCP Registry modal.
type MCPTab int

const (
	MCPTabConnected MCPTab = iota
	MCPTabCatalog
	MCPTabGuide
	MCPTabHelp
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
		Name:        "github-mcp",
		Transport:   "stdio · python",
		ToolCount:   7,
		Status:      "● Online",
		Description: "GitHub repositories search, issue tracker, pull requests, file inspector & commits list.",
		Tools: []string{
			"github_search_repositories", "github_get_repository", "github_list_issues",
			"github_create_issue", "github_list_pull_requests", "github_get_file_contents", "github_list_commits",
		},
	},
	{
		Name:        "spotify-mcp",
		Transport:   "stdio · python",
		ToolCount:   5,
		Status:      "● Online",
		Description: "Spotify track & playlist search, player status, playback control & volume adjust.",
		Tools: []string{
			"spotify_search", "spotify_get_current_playback", "spotify_playback_control",
			"spotify_set_volume", "spotify_list_user_playlists",
		},
	},
	{
		Name:        "pihu-whatsapp-mcp",
		Transport:   "stdio · python+go",
		ToolCount:   11,
		Status:      "● Online",
		Description: "WhatsApp messaging: send/receive messages, search contacts, list chats, media download & voice notes.",
		Tools: []string{
			"search_contacts", "list_messages", "list_chats", "get_chat",
			"get_direct_chat_by_contact", "get_contact_chats", "get_last_interaction",
			"send_message", "send_file", "send_audio_message", "download_media",
		},
	},
}

var CommunityMCPCatalog = []CommunityMCPItem{
	{
		ID:          "google-workspace",
		DisplayName: "Google Workspace MCP",
		Category:    "Productivity",
		Description: "Gmail send/search, Google Calendar, Drive search, Docs editor & Sheets",
		InstallCmd:  "pihu mcp install google-workspace",
		Prereqs:     "Python 3.10+ & Google OAuth Credentials",
		EnvVars:     []string{"GOOGLE_CLIENT_ID=...", "GOOGLE_CLIENT_SECRET=..."},
		ConfigSnippet: `{\n  "google-workspace": {\n    "command": "python",\n    "args": ["-m", "mcp_server_google_workspace"]\n  }\n}`,
		ToolsProvided: []string{"gmail_search", "gmail_send", "calendar_list_events", "drive_search", "docs_create", "sheets_read"},
		GuideSteps: []string{
			"1. Run: pihu mcp install google-workspace",
			"2. Export GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment",
			"3. AI Agent will be able to search emails, create events, and edit Google Docs",
		},
	},
	{
		ID:          "github",
		DisplayName: "GitHub Integration MCP",
		Category:    "Developer Tools",
		Description: "Create PRs, issues, read commits, workflows, and search repository code",
		InstallCmd:  "pihu mcp install github",
		Prereqs:     "GitHub Personal Access Token (GITHUB_TOKEN)",
		EnvVars:     []string{"GITHUB_PERSONAL_ACCESS_TOKEN=ghp_yourTokenHere"},
		ConfigSnippet: `{\n  "github": {\n    "command": "python",\n    "args": ["pihu_github_mcp.py"]\n  }\n}`,
		ToolsProvided: []string{"github_search_repositories", "github_get_repository", "github_list_issues", "github_create_issue", "github_list_pull_requests"},
		GuideSteps: []string{
			"1. Run: pihu mcp install github",
			"2. Set GITHUB_TOKEN in your environment or .env file",
			"3. AI Agent can inspect issues, search code, and manage GitHub repositories",
		},
	},
	{
		ID:          "spotify",
		DisplayName: "Spotify Player & Search MCP",
		Category:    "Media",
		Description: "Spotify track & playlist search, playback control, volume adjust & current playing track",
		InstallCmd:  "pihu mcp install spotify",
		Prereqs:     "Spotify Premium & SPOTIFY_ACCESS_TOKEN",
		EnvVars:     []string{"SPOTIFY_ACCESS_TOKEN=..."},
		ConfigSnippet: `{\n  "spotify": {\n    "command": "python",\n    "args": ["pihu_spotify_mcp.py"]\n  }\n}`,
		ToolsProvided: []string{"spotify_search", "spotify_get_current_playback", "spotify_playback_control", "spotify_set_volume"},
		GuideSteps: []string{
			"1. Run: pihu mcp install spotify",
			"2. Export SPOTIFY_ACCESS_TOKEN",
			"3. Control playback and search music directly from PIHU AI Agent",
		},
	},
	{
		ID:          "sqlite",
		DisplayName: "SQLite Database MCP",
		Category:    "Database",
		Description: "Query, introspect, and execute SQL across local SQLite databases",
		InstallCmd:  "pihu mcp install sqlite",
		Prereqs:     "Python 3.10+ (pip)",
		EnvVars:     []string{"SQLITE_DB_PATH=/path/to/database.db"},
		ConfigSnippet: `{\n  "sqlite": {\n    "command": "python",\n    "args": ["-m", "mcp_server_sqlite", "--db-path", "./app.db"]\n  }\n}`,
		ToolsProvided: []string{"read_query", "write_query", "create_table", "list_tables", "describe_table"},
		GuideSteps: []string{
			"1. Run: pihu mcp install sqlite",
			"2. Specify your SQLite database file path in args or env",
			"3. Restart PIHU or run /mcp to start querying SQLite databases natively",
		},
	},
	{
		ID:          "postgres",
		DisplayName: "PostgreSQL Database MCP",
		Category:    "Database",
		Description: "Connect and manage PostgreSQL schemas, queries, migrations and tables",
		InstallCmd:  "pihu mcp install postgres",
		Prereqs:     "PostgreSQL Database URI & Python 3.10+",
		EnvVars:     []string{"POSTGRES_URL=postgresql://user:pass@localhost:5432/dbname"},
		ConfigSnippet: `{\n  "postgres": {\n    "command": "python",\n    "args": ["-m", "mcp_server_postgres", "postgresql://user:pass@localhost:5432/dbname"]\n  }\n}`,
		ToolsProvided: []string{"query", "execute", "list_schemas", "list_tables", "describe_table"},
		GuideSteps: []string{
			"1. Run: pihu mcp install postgres",
			"2. Set POSTGRES_URL in your .env",
			"3. AI agent will be able to analyze table schemas and execute SQL",
		},
	},
	{
		ID:          "docker",
		DisplayName: "Docker Engine MCP",
		Category:    "DevOps & Cloud",
		Description: "Inspect, start, stop containers, view container logs, and manage images",
		InstallCmd:  "pihu mcp install docker",
		Prereqs:     "Docker Desktop / Docker Daemon running locally",
		EnvVars:     []string{"DOCKER_HOST=unix:///var/run/docker.sock"},
		ConfigSnippet: `{\n  "docker": {\n    "command": "python",\n    "args": ["-m", "mcp_server_docker"]\n  }\n}`,
		ToolsProvided: []string{"list_containers", "start_container", "stop_container", "get_logs", "list_images"},
		GuideSteps: []string{
			"1. Run: pihu mcp install docker",
			"2. Ensure Docker daemon or Docker Desktop is running",
			"3. PIHU can monitor containers & dev servers",
		},
	},
	{
		ID:          "puppeteer",
		DisplayName: "Puppeteer Web Automation MCP",
		Category:    "Web & Scraping",
		Description: "Headless Chrome automation, full-page screenshots, and interactive DOM inspection",
		InstallCmd:  "pihu mcp install puppeteer",
		Prereqs:     "Node.js 18+ (bundled Chromium)",
		EnvVars:     nil,
		ConfigSnippet: `{\n  "puppeteer": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-puppeteer"]\n  }\n}`,
		ToolsProvided: []string{"navigate", "screenshot", "click", "fill", "evaluate_javascript", "hover"},
		GuideSteps: []string{
			"1. Run: pihu mcp install puppeteer",
			"2. Agent can autonomously browse web pages, take screenshots, and test UI components",
		},
	},
	{
		ID:          "fetch",
		DisplayName: "Universal Fetch & Web Scraper MCP",
		Category:    "Web & Scraping",
		Description: "Fetch and convert web pages into clean LLM-friendly markdown",
		InstallCmd:  "pihu mcp install fetch",
		Prereqs:     "Python 3.10+",
		EnvVars:     nil,
		ConfigSnippet: `{\n  "fetch": {\n    "command": "python",\n    "args": ["-m", "mcp_server_fetch"]\n  }\n}`,
		ToolsProvided: []string{"fetch_url", "fetch_markdown", "extract_text", "extract_html"},
		GuideSteps: []string{
			"1. Run: pihu mcp install fetch",
			"2. Use PIHU to ingest web articles, documentation, and live APIs",
		},
	},
	{
		ID:          "brave-search",
		DisplayName: "Brave Web Search API MCP",
		Category:    "Search",
		Description: "Privacy-focused real-time web search and index querying",
		InstallCmd:  "pihu mcp install brave-search",
		Prereqs:     "Brave Search API Key",
		EnvVars:     []string{"BRAVE_API_KEY=BSA_yourBraveApiKey"},
		ConfigSnippet: `{\n  "brave-search": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-brave-search"]\n  }\n}`,
		ToolsProvided: []string{"brave_web_search", "brave_local_search"},
		GuideSteps: []string{
			"1. Run: pihu mcp install brave-search",
			"2. Export BRAVE_API_KEY",
		},
	},
	{
		ID:          "slack",
		DisplayName: "Slack Workspace MCP",
		Category:    "Productivity",
		Description: "Read channels, send messages, threads, and workspace notifications",
		InstallCmd:  "pihu mcp install slack",
		Prereqs:     "Slack Bot Token (xoxb-...)",
		EnvVars:     []string{"SLACK_BOT_TOKEN=xoxb-..."},
		ConfigSnippet: `{\n  "slack": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-slack"]\n  }\n}`,
		ToolsProvided: []string{"list_channels", "post_message", "reply_to_thread"},
		GuideSteps: []string{
			"1. Run: pihu mcp install slack",
			"2. Export SLACK_BOT_TOKEN",
			"3. PIHU agent can send and read Slack messages",
		},
	},
	{
		ID:          "redis",
		DisplayName: "Redis Cache & Key-Value MCP",
		Category:    "Database",
		Description: "Introspect keys, execute Redis commands, monitor pub/sub and memory stats",
		InstallCmd:  "pihu mcp install redis",
		Prereqs:     "Redis server running (local or cloud)",
		EnvVars:     []string{"REDIS_URL=redis://localhost:6379"},
		ConfigSnippet: `{\n  "redis": {\n    "command": "python",\n    "args": ["-m", "mcp_server_redis", "--url", "redis://localhost:6379"]\n  }\n}`,
		ToolsProvided: []string{"get_key", "set_key", "delete_key", "list_keys", "redis_info"},
		GuideSteps: []string{
			"1. Run: pihu mcp install redis",
			"2. Configure REDIS_URL",
		},
	},
	{
		ID:          "notion",
		DisplayName: "Notion Workspace MCP",
		Category:    "Productivity",
		Description: "Read and create Notion pages, query databases, append blocks and sync notes",
		InstallCmd:  "pihu mcp install notion",
		Prereqs:     "Notion Internal Integration Token (secret_...)",
		EnvVars:     []string{"NOTION_API_KEY=secret_yourNotionToken"},
		ConfigSnippet: `{\n  "notion": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-notion"]\n  }\n}`,
		ToolsProvided: []string{"search_pages", "read_page", "create_page", "query_database"},
		GuideSteps: []string{
			"1. Run: pihu mcp install notion",
			"2. Configure NOTION_API_KEY",
		},
	},
	{
		ID:          "whatsapp",
		DisplayName: "PIHU WhatsApp MCP",
		Category:    "Communication",
		Description: "Send & receive WhatsApp messages, search contacts, chat history, media download & voice notes",
		InstallCmd:  "pihu mcp install whatsapp",
		Prereqs:     "WhatsApp account, Go 1.21+ (for bridge), Python 3.10+ (for MCP server)",
		EnvVars:     nil,
		ConfigSnippet: `{\n  "pihu-whatsapp-mcp": {\n    "command": "uv",\n    "args": ["--directory", "servers/pihu-whatsapp-mcp/whatsapp-mcp-server", "run", "main.py"]\n  }\n}`,
		ToolsProvided: []string{"search_contacts", "list_messages", "list_chats", "send_message", "send_file", "send_audio_message", "download_media"},
		GuideSteps: []string{
			"1. Run: pihu mcp install whatsapp",
			"2. Build the Go bridge: cd whatsapp-bridge && go build -o bridge .",
			"3. Start bridge (first time: scan QR code): ./bridge",
			"4. PIHU agent can send/receive WhatsApp messages, search contacts & download media",
		},
	},
}

const (
	mcpIcoLoaded = "●"
	mcpIcoAvail  = "○"
	mcpIcoMark   = "◈"
	mcpIcoArrow  = "▸"
	mcpIcoDot    = "·"
	mcpIcoHelp   = "?"
)

type rawMCPConfig struct {
	Servers map[string]struct {
		Command string            `json:"command"`
		Args    []string          `json:"args"`
		Env     map[string]string `json:"env"`
	} `json:"servers"`
}

// GetRealConnectedServers dynamically inspects MCP configurations on disk (config.json, installed.json)
// and live services (WhatsApp bridge, Google OAuth) to return the actual connected servers with real status.
func GetRealConnectedServers() []ConnectedMCPServer {
	paths := []string{
		"src-tauri/pihu_mcps/mcp/config.json",
		"../mcp/config.json",
		"mcp/config.json",
		"../../mcp/config.json",
	}
	if home, err := os.UserHomeDir(); err == nil {
		paths = append(paths, filepath.Join(home, ".pihu", "mcp_config.json"))
		paths = append(paths, filepath.Join(home, ".pihu", "mcp", "installed.json"))
	}

	var foundPath string
	var rawData []byte
	for _, p := range paths {
		if data, err := os.ReadFile(p); err == nil && len(data) > 0 {
			foundPath = p
			rawData = data
			break
		}
	}

	if foundPath == "" || len(rawData) == 0 {
		return ActiveConnectedServers
	}

	var cfg rawMCPConfig
	if err := json.Unmarshal(rawData, &cfg); err != nil || len(cfg.Servers) == 0 {
		return ActiveConnectedServers
	}

	// Check WhatsApp bridge live status
	waOnline := false
	waAuth := false
	httpClient := http.Client{Timeout: 350 * time.Millisecond}
	if resp, err := httpClient.Get("http://localhost:8080/api/status"); err == nil && resp.StatusCode == 200 {
		defer resp.Body.Close()
		var st struct {
			Connected bool `json:"connected"`
			LoggedIn  bool `json:"logged_in"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&st); err == nil {
			waOnline = st.Connected
			waAuth = st.LoggedIn
		}
	}

	knownServers := map[string]ConnectedMCPServer{
		"pihu-file-mcp": {
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
		"pihu-system-mcp": {
			Name:        "pihu-system-mcp",
			Transport:   "stdio · python",
			ToolCount:   7,
			Status:      "● Online",
			Description: "Local system inspect, shell execution, memory usage, CPU, processes & native notifications.",
			Tools: []string{
				"get_system_info", "run_shell", "list_processes", "kill_process", "send_notification", "get_env", "disk_usage",
			},
		},
		"pihu-web-search-mcp": {
			Name:        "pihu-web-search-mcp",
			Transport:   "stdio · python",
			ToolCount:   6,
			Status:      "● Online",
			Description: "Realtime web search, full web page scraper, markdown parser, download file & URL fetch.",
			Tools: []string{
				"web_search", "web_fetch", "web_search_and_read", "web_download_file", "extract_links", "fetch_metadata",
			},
		},
		"google-workspace-mcp": {
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
		"github-mcp": {
			Name:        "github-mcp",
			Transport:   "stdio · python",
			ToolCount:   7,
			Status:      "● Online",
			Description: "GitHub repositories search, issue tracker, pull requests, file inspector & commits list.",
			Tools: []string{
				"github_search_repositories", "github_get_repository", "github_list_issues",
				"github_create_issue", "github_list_pull_requests", "github_get_file_contents", "github_list_commits",
			},
		},
		"spotify-mcp": {
			Name:        "spotify-mcp",
			Transport:   "stdio · python",
			ToolCount:   5,
			Status:      "● Online",
			Description: "Spotify track & playlist search, player status, playback control & volume adjust.",
			Tools: []string{
				"spotify_search", "spotify_get_current_playback", "spotify_playback_control",
				"spotify_set_volume", "spotify_list_user_playlists",
			},
		},
		"pihu-whatapp-mcp": {
			Name:        "pihu-whatsapp-mcp",
			Transport:   "stdio · python+go",
			ToolCount:   11,
			Status:      "● Online",
			Description: "WhatsApp messaging: send/receive messages, search contacts, list chats, media download & voice notes.",
			Tools: []string{
				"search_contacts", "list_messages", "list_chats", "get_chat",
				"get_direct_chat_by_contact", "get_contact_chats", "get_last_interaction",
				"send_message", "send_file", "send_audio_message", "download_media",
			},
		},
		"pihu-whatsapp-mcp": {
			Name:        "pihu-whatsapp-mcp",
			Transport:   "stdio · python+go",
			ToolCount:   11,
			Status:      "● Online",
			Description: "WhatsApp messaging: send/receive messages, search contacts, list chats, media download & voice notes.",
			Tools: []string{
				"search_contacts", "list_messages", "list_chats", "get_chat",
				"get_direct_chat_by_contact", "get_contact_chats", "get_last_interaction",
				"send_message", "send_file", "send_audio_message", "download_media",
			},
		},
		"pihu-project-mcp": {
			Name:        "pihu-project-mcp",
			Transport:   "stdio · node",
			ToolCount:   6,
			Status:      "● Online",
			Description: "Multi-language project scaffolding, runner, diagnosis, health, and server supervisor.",
			Tools: []string{
				"scaffold_project", "run_diagnostics", "check_health", "test_project", "manage_process",
			},
		},
	}

	var results []ConnectedMCPServer
	for name, srvCfg := range cfg.Servers {
		if known, ok := knownServers[name]; ok {
			if strings.Contains(name, "whatsapp") || strings.Contains(name, "whatapp") {
				if waOnline || waAuth {
					known.Status = "● Online"
				} else {
					known.Status = "○ Ready (Auth /mcp)"
				}
			}
			results = append(results, known)
		} else {
			rt := "stdio · python"
			if strings.Contains(srvCfg.Command, "node") {
				rt = "stdio · node"
			} else if strings.Contains(srvCfg.Command, "uv") {
				rt = "stdio · uv"
			}
			results = append(results, ConnectedMCPServer{
				Name:        name,
				Transport:   rt,
				ToolCount:   4,
				Status:      "● Online",
				Description: fmt.Sprintf("Configured MCP service (%s). Registered in %s", name, filepath.Base(foundPath)),
				Tools:       []string{name + "_query", name + "_exec"},
			})
		}
	}

	if len(results) == 0 {
		return ActiveConnectedServers
	}
	return results
}

func FetchLiveMCPCatalog() []CommunityMCPItem {
	endpoints := []string{
		"http://localhost:8080/api/v1/mcp/catalog",
		"https://pihu.nfks.co.in/api/v1/mcp/catalog",
	}
	client := http.Client{Timeout: 1500 * time.Millisecond}
	for _, url := range endpoints {
		resp, err := client.Get(url)
		if err == nil && resp.StatusCode == 200 {
			defer resp.Body.Close()
			var items []CommunityMCPItem
			if err := json.NewDecoder(resp.Body).Decode(&items); err == nil && len(items) > 0 {
				return items
			}
		}
	}
	return CommunityMCPCatalog
}

// RenderMCPRegistryModal renders a lazy.nvim-style MCP registry overlay
// using the active PIHU theme (transparent wallpaper or solid base).
func RenderMCPRegistryModal(
	activeTab MCPTab,
	connected []ConnectedMCPServer,
	catalog []CommunityMCPItem,
	selectedConnectedIdx int,
	selectedCatalogIdx int,
	w, h int,
) string {
	if len(connected) == 0 {
		connected = GetRealConnectedServers()
	}
	if len(catalog) == 0 {
		catalog = FetchLiveMCPCatalog()
	}
	modalW := int(float64(w) * 0.90)
	if modalW < 96 {
		modalW = min(w-2, 96)
	}
	if modalW > 118 {
		modalW = 118
	}
	if modalW > w-2 {
		modalW = max(36, w-2)
	}

	modalH := int(float64(h) * 0.82)
	if modalH < 16 {
		modalH = min(h-2, 16)
	}
	if modalH > 32 {
		modalH = 32
	}
	if modalH > h-2 {
		modalH = max(10, h-2)
	}

	padX := 1
	borderCols := 2
	innerW := modalW - borderCols - (padX * 2)
	if innerW < 40 {
		innerW = 40
	}

	innerH := modalH - 4
	if innerH < 10 {
		innerH = 10
	}

	totalTools := 0
	for _, srv := range connected {
		totalTools += srv.ToolCount
	}

	var rows []string
	rows = append(rows, mcpLazyHeaderLine1(innerW))
	rows = append(rows, mcpPadRow("", innerW))
	rows = append(rows, mcpLazyHeaderLine2(activeTab, innerW))
	rows = append(rows, mcpRule(innerW))
	rows = append(rows, mcpPadRow(
		mcpMuted(fmt.Sprintf("%s  Total  %s  %d servers  %s  %d tools  %s  %d catalog",
			mcpIcoMark, mcpIcoDot, len(connected), mcpIcoDot, totalTools, mcpIcoDot, len(catalog))),
		innerW,
	))
	rows = append(rows, mcpPadRow("", innerW))

	switch activeTab {
	case MCPTabConnected:
		rows = append(rows, mcpLazyConnected(connected, selectedConnectedIdx, innerW)...)
	case MCPTabCatalog:
		budget := innerH - 9
		if budget < 4 {
			budget = 4
		}
		rows = append(rows, mcpLazyCatalog(catalog, selectedCatalogIdx, innerW, budget)...)
	case MCPTabGuide:
		rows = append(rows, mcpLazyGuide(catalog, selectedCatalogIdx, innerW)...)
	case MCPTabHelp:
		rows = append(rows, mcpLazyHelp(innerW)...)
	}

	creditText := "developed by Mayank Jha"
	creditRow := lipgloss.NewStyle().
		Width(innerW).
		Align(lipgloss.Right).
		Foreground(colMuted).
		Italic(true).
		Render(creditText)

	for len(rows) < innerH-2 {
		rows = append(rows, mcpPadRow("", innerW))
	}
	if len(rows) > innerH-2 {
		rows = rows[:innerH-2]
	}
	rows = append(rows, mcpRule(innerW), creditRow)

	body := strings.Join(rows, "\n")
	frame := lipgloss.NewStyle().
		Width(innerW).
		Padding(1, padX).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve)
	if !TransparentBackground {
		frame = frame.Background(colBase)
	}
	return frame.Render(body)
}

func mcpLazyHeaderLine1(innerW int) string {
	thunderIcon := lipgloss.NewStyle().Foreground(colYellow).Bold(true).Render("⚡")
	brand := lipgloss.NewStyle().
		Bold(true).
		Foreground(colCrust).
		Background(colPeach).
		Padding(0, 1).
		Render("PIHU MCPS")
	subtitle := lipgloss.NewStyle().Foreground(colSubtext).Bold(true).Render("  " + thunderIcon + "  MCP Registry")
	return mcpPadRow(brand+subtitle, innerW)
}

func mcpLazyHeaderLine2(activeTab MCPTab, innerW int) string {
	gap := "   "
	actions := []string{
		mcpAction("Connected", "1", activeTab == MCPTabConnected, colGreen),
		mcpAction("Catalog", "2", activeTab == MCPTabCatalog, colSky),
		mcpAction("Guide", "3", activeTab == MCPTabGuide, colPeach),
		mcpAction("Install", "I", false, colGreen),
		mcpAction("Check", "C", false, colBlue),
		mcpAction("Help", "?", activeTab == MCPTabHelp, colYellow),
	}
	return mcpPadRow(strings.Join(actions, gap), innerW)
}

func mcpAction(label, key string, active bool, accent lipgloss.Color) string {
	content := fmt.Sprintf("%s [ %s ]", label, key)
	if active {
		return lipgloss.NewStyle().
			Bold(true).
			Foreground(colCrust).
			Background(accent).
			Padding(0, 1).
			Render(content)
	}

	labelPart := lipgloss.NewStyle().Foreground(lipgloss.Color("#ffffff")).Render(label)
	keyPart := lipgloss.NewStyle().Foreground(colYellow).Bold(true).Render("[ " + key + " ]")
	return labelPart + " " + keyPart
}

func mcpSection(icon, label string, count int) string {
	head := lipgloss.NewStyle().Foreground(colMuted).Bold(true).
		Render(fmt.Sprintf("%s  %s (%d)", icon, label, count))
	return head
}

func mcpMuted(s string) string {
	return lipgloss.NewStyle().Foreground(colMuted).Render(s)
}

func mcpRule(w int) string {
	if w < 1 {
		w = 1
	}
	return lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", w))
}

func mcpPadRow(s string, w int) string {
	return lipgloss.NewStyle().Width(w).MaxWidth(w).Render(s)
}

func mcpLazyConnected(connected []ConnectedMCPServer, selected int, innerW int) []string {
	var rows []string
	rows = append(rows, mcpPadRow(mcpSection(mcpIcoLoaded, "Loaded", len(connected)), innerW))
	rows = append(rows, mcpPadRow("", innerW))

	nameW := 24
	for i, srv := range connected {
		selectedRow := i == selected
		runtime := mcpRuntime(srv.Transport)

		bullet := lipgloss.NewStyle().Foreground(colGreen).Render(mcpIcoLoaded)
		nameSt := lipgloss.NewStyle().Foreground(colText).Width(nameW)
		if selectedRow {
			nameSt = lipgloss.NewStyle().Foreground(colText).Bold(true).Width(nameW)
			bullet = lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render(mcpIcoLoaded)
		}

		line := lipgloss.JoinHorizontal(lipgloss.Left,
			bullet,
			"  ",
			nameSt.Render(srv.Name),
			"  ",
			lipgloss.NewStyle().Foreground(colMuted).Render(fmt.Sprintf("%s %d tools", mcpIcoMark, srv.ToolCount)),
			"    ",
			lipgloss.NewStyle().Foreground(colMauve).Render(mcpIcoArrow+" "+runtime),
			"    ",
			lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render(mcpIcoLoaded+"  online"),
		)
		rows = append(rows, mcpPadRow(line, innerW))

		if selectedRow {
			rows = append(rows, mcpPadRow(
				"    "+lipgloss.NewStyle().Foreground(colSubtext).Render(mcpFit(srv.Description, innerW-6)),
				innerW,
			))
			shown := min(6, len(srv.Tools))
			var parts []string
			for t := 0; t < shown; t++ {
				parts = append(parts, mcpHashStyle(t).Render(mcpIcoMark+" "+srv.Tools[t]))
			}
			if len(srv.Tools) > shown {
				parts = append(parts, lipgloss.NewStyle().Foreground(colMuted).Render(mcpIcoDot+"  more"))
			}
			rows = append(rows, mcpPadRow("    "+strings.Join(parts, "   "), innerW))
		}
		rows = append(rows, mcpPadRow("", innerW))
	}
	return rows
}

func mcpLazyCatalog(catalog []CommunityMCPItem, selected, innerW, budget int) []string {
	var rows []string
	rows = append(rows, mcpPadRow(mcpSection(mcpIcoAvail, "Not Installed", len(catalog)), innerW))
	rows = append(rows, mcpPadRow("", innerW))

	maxShow := budget / 2
	if maxShow < 4 {
		maxShow = 4
	}
	start := 0
	if selected >= maxShow {
		start = selected - maxShow + 1
	}
	end := min(len(catalog), start+maxShow)
	nameW := 28

	for i := start; i < end; i++ {
		item := catalog[i]
		selectedRow := i == selected

		bullet := lipgloss.NewStyle().Foreground(colMuted).Render(mcpIcoAvail)
		nameSt := lipgloss.NewStyle().Foreground(colText).Width(nameW)
		if selectedRow {
			bullet = lipgloss.NewStyle().Foreground(colSky).Bold(true).Render(mcpIcoAvail)
			nameSt = lipgloss.NewStyle().Foreground(colText).Bold(true).Width(nameW)
		}

		line := lipgloss.JoinHorizontal(lipgloss.Left,
			bullet,
			"  ",
			nameSt.Render(item.DisplayName),
			"  ",
			lipgloss.NewStyle().Foreground(colMauve).Render(mcpIcoArrow+" "+item.Category),
			"    ",
			lipgloss.NewStyle().Foreground(colSky).Bold(true).Render(mcpIcoMark+"  available"),
		)
		rows = append(rows, mcpPadRow(line, innerW))

		if selectedRow {
			rows = append(rows, mcpPadRow(
				"    "+lipgloss.NewStyle().Foreground(colSubtext).Render(mcpFit(item.Description, innerW-6)),
				innerW,
			))
			rows = append(rows, mcpPadRow(
				"    "+lipgloss.NewStyle().Foreground(colYellow).Render(mcpIcoArrow+" install  ")+
					lipgloss.NewStyle().Foreground(colGreen).Render(mcpFit(item.InstallCmd, innerW-16)),
				innerW,
			))
		}
		rows = append(rows, mcpPadRow("", innerW))
	}
	return rows
}

func mcpLazyGuide(catalog []CommunityMCPItem, selected, innerW int) []string {
	if selected < 0 || selected >= len(catalog) {
		return []string{mcpPadRow(mcpMuted("Select a catalog item (2), then press Enter for the setup guide."), innerW)}
	}
	item := catalog[selected]
	var rows []string

	rows = append(rows, mcpPadRow(mcpSection(mcpIcoMark, "Setup Guide", 1), innerW))
	rows = append(rows, mcpPadRow("", innerW))
	title := lipgloss.NewStyle().Foreground(colText).Bold(true).Render(item.DisplayName) +
		"    " + lipgloss.NewStyle().Foreground(colMauve).Render(mcpIcoArrow+" "+item.Category)
	rows = append(rows, mcpPadRow(mcpIcoLoaded+"  "+title, innerW))
	rows = append(rows, mcpPadRow("    "+lipgloss.NewStyle().Foreground(colSubtext).Render(mcpFit(item.Description, innerW-6)), innerW))
	rows = append(rows, mcpPadRow("", innerW))

	rows = append(rows, mcpPadRow(lipgloss.NewStyle().Foreground(colMuted).Bold(true).Render(mcpIcoMark+"  Install"), innerW))
	rows = append(rows, mcpPadRow("    "+mcpHashStyle(0).Render("cmd")+"    "+lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render(item.InstallCmd), innerW))
	rows = append(rows, mcpPadRow("    "+mcpHashStyle(1).Render("need")+"   "+lipgloss.NewStyle().Foreground(colText).Render(item.Prereqs), innerW))
	rows = append(rows, mcpPadRow("", innerW))

	if len(item.EnvVars) > 0 {
		rows = append(rows, mcpPadRow(lipgloss.NewStyle().Foreground(colMuted).Bold(true).Render(mcpIcoMark+"  Environment"), innerW))
		for i, ev := range item.EnvVars {
			rows = append(rows, mcpPadRow("    "+mcpHashStyle(i+2).Render("env")+"    "+lipgloss.NewStyle().Foreground(colPeach).Render(ev), innerW))
		}
		rows = append(rows, mcpPadRow("", innerW))
	}

	rows = append(rows, mcpPadRow(lipgloss.NewStyle().Foreground(colMuted).Bold(true).Render(mcpIcoMark+"  mcp/config.json"), innerW))
	snippet := strings.ReplaceAll(item.ConfigSnippet, `\n`, "\n")
	for _, line := range strings.Split(snippet, "\n") {
		rows = append(rows, mcpPadRow("    "+lipgloss.NewStyle().Foreground(colMauve).Render(mcpFit(line, innerW-6)), innerW))
	}
	rows = append(rows, mcpPadRow("", innerW))

	rows = append(rows, mcpPadRow(lipgloss.NewStyle().Foreground(colMuted).Bold(true).Render(mcpIcoMark+"  Tools"), innerW))
	var tools []string
	for i, t := range item.ToolsProvided {
		tools = append(tools, mcpHashStyle(i).Render(mcpIcoMark+" "+t))
	}
	rows = append(rows, mcpPadRow("    "+strings.Join(tools, "   "), innerW))
	return rows
}

func mcpLazyHelp(innerW int) []string {
	var rows []string
	rows = append(rows, mcpPadRow(mcpSection(mcpIcoHelp, "Help", 8), innerW))
	rows = append(rows, mcpPadRow("", innerW))
	rows = append(rows, mcpPadRow(lipgloss.NewStyle().Foreground(colSubtext).Render("Keyboard bindings for the MCP Registry"), innerW))
	rows = append(rows, mcpPadRow("", innerW))

	type bind struct {
		key, desc string
		color     lipgloss.Color
	}
	binds := []bind{
		{"1 / C", "Connected servers (loaded runtime)", colGreen},
		{"2", "Installable catalog", colSky},
		{"3 / G", "Setup guide for selected catalog item", colPeach},
		{"? / 4", "This help view", colYellow},
		{"I / Enter", "Install hint or open setup guide", colGreen},
		{"j / k", "Move selection up and down", colBlue},
		{"Tab", "Cycle Connected, Catalog, Guide, Help", colMauve},
		{"Esc", "Back one view, or close the registry", colRed},
	}
	for _, b := range binds {
		key := lipgloss.NewStyle().Foreground(b.color).Bold(true).Width(12).Render(b.key)
		desc := lipgloss.NewStyle().Foreground(colText).Render(b.desc)
		rows = append(rows, mcpPadRow("  "+mcpIcoArrow+"  "+key+"  "+desc, innerW))
		rows = append(rows, mcpPadRow("", innerW))
	}
	return rows
}

func mcpRuntime(transport string) string {
	parts := strings.Split(transport, "·")
	if len(parts) == 0 {
		return transport
	}
	return strings.TrimSpace(parts[len(parts)-1])
}

func mcpHashStyle(i int) lipgloss.Style {
	palette := []lipgloss.Color{colGreen, colMauve, colYellow, colPeach, colSky, colBlue, colTeal}
	return lipgloss.NewStyle().Foreground(palette[i%len(palette)])
}

func mcpFit(s string, n int) string {
	if n <= 3 || lipgloss.Width(s) <= n {
		return s
	}
	runes := []rune(s)
	keep := n - 3
	if keep < 1 {
		keep = 1
	}
	if keep > len(runes) {
		keep = len(runes)
	}
	return string(runes[:keep]) + "..."
}
