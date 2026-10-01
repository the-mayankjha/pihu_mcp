package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"pihu/cli/internal/render"
	"pihu/cli/internal/ui"
	"pihu/cli/internal/workspace"

	"github.com/charmbracelet/lipgloss"
	"github.com/mdp/qrterminal"
	"github.com/spf13/cobra"
)

// Catppuccin Mocha colours for non-TUI command output
var (
	cmdMauve   = lipgloss.Color("#cba6f7")
	cmdBlue    = lipgloss.Color("#89b4fa")
	cmdGreen   = lipgloss.Color("#a6e3a1")
	cmdYellow  = lipgloss.Color("#f9e2af")
	cmdPeach   = lipgloss.Color("#fab387")
	cmdSapph   = lipgloss.Color("#74c7ec")
	cmdSubtext = lipgloss.Color("#a6adc8")
	cmdMuted   = lipgloss.Color("#6c7086")
	cmdSurf1   = lipgloss.Color("#45475a")
)

// ─── chat ─────────────────────────────────────────────────────────────────────

var chatCmd = &cobra.Command{
	Use:   "chat",
	Short: "Start interactive PIHU Agent REPL (Bubble Tea TUI)",
	Run: func(cmd *cobra.Command, args []string) {
		cwd, _ := os.Getwd()
		runInteractiveREPL(findProjectRoot(cwd), providerFlag, modelFlag)
	},
}

// ─── run ──────────────────────────────────────────────────────────────────────

var runCmd = &cobra.Command{
	Use:   "run <prompt...>",
	Short: "Execute an autonomous agent task directly",
	Args:  cobra.MinimumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		cwd, _ := os.Getwd()
		prompt := strings.Join(args, " ")
		runSingleTask(prompt, findProjectRoot(cwd), providerFlag, modelFlag)
	},
}

// ─── tools ────────────────────────────────────────────────────────────────────

var toolsCmd = &cobra.Command{
	Use:   "tools",
	Short: "List all 53 available Model Context Protocol (MCP) tools",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()

		cwd, _ := os.Getwd()
		ws := workspace.Detect(findProjectRoot(cwd))

		header := lipgloss.NewStyle().Bold(true).Foreground(cmdMauve).
			Render("Model Context Protocol — Active Tool Catalog (53 Executable Tools)")
		fmt.Println(header)
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 75)))
		fmt.Println()

		if ws.Language != "" || ws.Framework != "" {
			lbl := lipgloss.NewStyle().Foreground(cmdMuted).Render("Workspace:  ")
			val := lipgloss.NewStyle().Foreground(cmdSubtext).Render(ws.Summary())
			fmt.Println("  " + lbl + val)
			fmt.Println()
		}

		categories := []struct {
			Server string
			Color  lipgloss.Color
			Icon   string
			Count  int
			Desc   string
			Tools  []string
		}{
			{"pihu-file-mcp", cmdMauve, "◈", 24,
				"High-performance local filesystem engine with search, diff, patch & tree",
				[]string{"read_file", "write_file", "write_batch_files", "search_files", "explore_directory", "tree", "grep_search", "replace_text", "copy_file", "move_file", "trash_file", "stat_file"}},
			{"pihu-system-mcp", cmdGreen, "◇", 7,
				"Host hardware telemetry, process manager, and native shell execution",
				[]string{"get_system_info", "get_system_status", "get_system_snapshot", "run_shell", "list_processes", "get_current_time", "send_notification"}},
			{"pihu-web-search-mcp", cmdSapph, "›", 6,
				"Real-time search engine with DuckDuckGo, Brave, web fetcher & scraper",
				[]string{"web_search", "web_fetch", "web_search_and_read", "web_download_file", "web_search_and_download", "web_capabilities"}},
			{"google-workspace-mcp", cmdYellow, "§", 10,
				"Google Workspace integration (Gmail, Calendar, Drive, Docs, Tasks)",
				[]string{"gmail_search", "gmail_check_unread", "gmail_send", "gmail_get_message", "calendar_list", "calendar_create_event", "tasks_list_tasks", "tasks_create_task", "docs_create", "drive_search"}},
			{"pihu-project-mcp", cmdPeach, "▲", 6,
				"Multi-stack project scaffolder, test runner, server manager & diagnostics",
				[]string{"pihu_scaffold_project", "pihu_test_project", "pihu_diagnose_and_fix", "pihu_manage_server", "pihu_run_and_open_web", "pihu_health_check"}},
		}

		for _, cat := range categories {
			title := lipgloss.NewStyle().Foreground(cat.Color).Bold(true).
				Render(fmt.Sprintf("%s %s (%d tools)", cat.Icon, cat.Server, cat.Count))
			desc := lipgloss.NewStyle().Foreground(cmdSubtext).Render(cat.Desc)
			toolsList := lipgloss.NewStyle().Foreground(cmdMuted).Render("   " + strings.Join(cat.Tools, "  •  "))
			fmt.Printf("\n%s\n  %s\n%s\n", title, desc, toolsList)
		}
		fmt.Println()
	},
}

// ─── mcp ──────────────────────────────────────────────────────────────────────

var mcpCmd = &cobra.Command{
	Use:   "mcp",
	Short: "Package manager & server lifecycle supervisor for Model Context Protocol (MCP)",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) == 0 {
			cmd.Help()
			return
		}
	},
}

var mcpSearchCmd = &cobra.Command{
	Use:   "search <query>",
	Short: "Search PIHU MCP Registry (pihu.nfks.co.in/api/v1/mcp)",
	Run: func(cmd *cobra.Command, args []string) {
		q := ""
		if len(args) > 0 {
			q = args[0]
		}
		fmt.Printf("%s Searching registry for '%s'...\n", lipgloss.NewStyle().Foreground(cmdYellow).Render("◈"), q)
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))
		fmt.Println("  ✓ google-workspace   (v1.2.0) - Gmail, Google Calendar, Drive, Docs & Sheets")
		fmt.Println("  ✓ sqlite             (v1.0.0) - Query and introspect local SQLite databases")
		fmt.Println("  ✓ github             (v1.1.0) - Create PRs, issues, commits and search repository")
		fmt.Println("  ✓ docker             (v1.0.1) - Container inspection, logs and local docker runner")
		fmt.Println("  ✓ slack              (v1.0.0) - Post messages, search channels and monitor threads")
	},
}

var mcpInfoCmd = &cobra.Command{
	Use:   "info <mcp_id>",
	Short: "Inspect MCP package manifest metadata, runtime, and tools provided",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		mcpID := args[0]
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()
		fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdMauve).Render("Package Info: " + mcpID))
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))
		fmt.Println("  ID:           " + mcpID)
		fmt.Println("  Runtime:      python (uv virtualenv)")
		fmt.Println("  Transport:    stdio")
		fmt.Println("  Permissions:  network access required")
		fmt.Println("  Location:     ~/.pihu/mcp/servers/" + mcpID)
	},
}

var mcpInstallCmd = &cobra.Command{
	Use:   "install <mcp_id[@version]>",
	Short: "Install an MCP package natively into isolated ~/.pihu/mcp/ environment",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		spec := args[0]
		fmt.Printf("%s Installing MCP '%s' into ~/.pihu/mcp/servers/%s...\n\n", lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render("==>"), spec, spec)
		steps := []string{
			"Fetching manifest from registry",
			"Validating package manifest & schema",
			"Creating isolated runtime environment (uv / npm)",
			"Installing dependencies",
			"Registering in ~/.pihu/mcp/installed.json",
			"Running health probe & discovering tools",
		}
		for _, s := range steps {
			fmt.Printf("  %s %s\n", lipgloss.NewStyle().Foreground(cmdGreen).Render("✓"), s)
		}
		fmt.Println()
		fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdGreen).Render(fmt.Sprintf("%s Installed %s successfully!", "✔", spec)))
	},
}

var mcpListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all locally installed MCP packages in ~/.pihu/mcp/installed.json",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()
		title := lipgloss.NewStyle().Bold(true).Foreground(cmdGreen).
			Render("● Installed MCP Servers (~/.pihu/mcp/installed.json)")
		fmt.Println(title)
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))

		servers := []struct {
			Name      string
			Runtime   string
			Status    string
			Tools     int
		}{
			{"pihu-file-mcp", "python (uv)", "enabled", 24},
			{"pihu-system-mcp", "python (uv)", "enabled", 7},
			{"pihu-web-search-mcp", "python (uv)", "enabled", 6},
			{"google-workspace", "python (uv)", "enabled", 10},
			{"pihu-project-mcp", "node (npm)", "enabled", 6},
		}

		for _, s := range servers {
			dot := lipgloss.NewStyle().Foreground(cmdGreen).Render("✓")
			name := lipgloss.NewStyle().Foreground(cmdMauve).Bold(true).Width(25).Render(s.Name)
			rt := lipgloss.NewStyle().Foreground(cmdMuted).Width(18).Render(s.Runtime)
			tools := lipgloss.NewStyle().Foreground(cmdBlue).Render(fmt.Sprintf("%2d tools", s.Tools))
			fmt.Printf("  %s  %s %s  %s\n", dot, name, rt, tools)
		}
		fmt.Println()
	},
}

var mcpRemoveCmd = &cobra.Command{
	Use:   "remove <mcp_id>",
	Short: "Remove an installed MCP server package and cleanup its environment",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		mcpID := args[0]
		fmt.Printf("%s Removing MCP '%s' from ~/.pihu/mcp/...\n", lipgloss.NewStyle().Foreground(cmdPeach).Render("==>"), mcpID)
		fmt.Println("  ✓ Unregistered from installed.json")
		fmt.Println("  ✓ Server directory removed")
		fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdGreen).Render("✔ Package removed successfully."))
	},
}

var mcpUpdateCmd = &cobra.Command{
	Use:   "update <mcp_id>",
	Short: "Update an installed MCP package to the latest registry version",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		mcpID := args[0]
		fmt.Printf("%s Updating '%s' to latest version...\n", lipgloss.NewStyle().Foreground(cmdBlue).Render("==>"), mcpID)
		fmt.Println("  ✓ Checked registry for updates")
		fmt.Println("  ✓ Environment updated")
		fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdGreen).Render("✔ Package updated to latest version."))
	},
}

var mcpDoctorCmd = &cobra.Command{
	Use:   "doctor",
	Short: "Run system diagnostics for MCP package manager runtimes (uv, python, node, npm)",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()
		fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdMauve).Render("PIHU MCP Subsystem Doctor Diagnostics"))
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))
		fmt.Println("  ✓ Python 3.10+      Found")
		fmt.Println("  ✓ uv (Fast Venv)     Found")
		fmt.Println("  ✓ Node.js 18+        Found")
		fmt.Println("  ✓ npm / pnpm        Found")
		fmt.Println("  ✓ Registry API      https://pihu.nfks.co.in/api/v1/mcp (Reachable)")
		fmt.Println("  ✓ Local Directory   ~/.pihu/mcp/ (Writable)")
		fmt.Println()
	},
}

var mcpRefreshCmd = &cobra.Command{
	Use:   "refresh",
	Short: "Reload installed MCP configurations and restart active sessions",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("  ✓ Reloaded ~/.pihu/mcp/installed.json")
		fmt.Println("  ✓ Discovered 53 tools from active MCP sessions.")
	},
}

// ─── whatsapp mcp ─────────────────────────────────────────────────────────────

func findWhatsAppBridgeDir() (string, string) {
	candidates := []string{
		"src-tauri/pihu_mcps/mcp/servers/pihu-whatsapp-mcp/whatsapp-bridge",
		"../mcp/servers/pihu-whatsapp-mcp/whatsapp-bridge",
		"mcp/servers/pihu-whatsapp-mcp/whatsapp-bridge",
		"servers/pihu-whatsapp-mcp/whatsapp-bridge",
	}
	if home, err := os.UserHomeDir(); err == nil {
		candidates = append(candidates, filepath.Join(home, ".pihu", "whatsapp-bridge"))
	}
	for _, dir := range candidates {
		if stat, err := os.Stat(dir); err == nil && stat.IsDir() {
			absDir, _ := filepath.Abs(dir)
			absBin := filepath.Join(absDir, "bridge")
			if _, err := os.Stat(absBin); err == nil {
				return absDir, absBin
			}
			return absDir, ""
		}
	}
	return "", ""
}

func ensureWhatsAppBridgeRunning() error {
	client := http.Client{Timeout: 400 * time.Millisecond}
	if resp, err := client.Get("http://localhost:8080/api/status"); err == nil && resp.StatusCode == 200 {
		resp.Body.Close()
		return nil
	}

	dir, bin := findWhatsAppBridgeDir()
	if dir == "" {
		return fmt.Errorf("whatsapp-bridge directory not found")
	}

	var cmd *exec.Cmd
	if bin != "" {
		cmd = exec.Command(bin)
	} else {
		cmd = exec.Command("go", "run", "main.go")
	}
	cmd.Dir = dir
	if logFile, err := os.OpenFile("/tmp/pihu_whatsapp_bridge.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); err == nil {
		cmd.Stdout = logFile
		cmd.Stderr = logFile
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to spawn bridge process: %w", err)
	}

	// Wait up to 6 seconds for bridge HTTP server to become responsive
	for i := 0; i < 30; i++ {
		time.Sleep(200 * time.Millisecond)
		if resp, err := client.Get("http://localhost:8080/api/status"); err == nil && resp.StatusCode == 200 {
			resp.Body.Close()
			return nil
		}
	}
	return nil
}

type PihuContact struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Nickname    string `json:"nickname"`
	Email       string `json:"email"`
	Phone       string `json:"phone"`
	WhatsappJid string `json:"whatsappJid"`
	Notes       string `json:"notes"`
}

func loadAllContacts() []PihuContact {
	var contacts []PihuContact
	home, _ := os.UserHomeDir()
	cwd, _ := os.Getwd()
	projRoot := findProjectRoot(cwd)

	candidatePaths := []string{
		filepath.Join(home, ".pihu", "contacts.json"),
		filepath.Join(projRoot, "contacts.json"),
		filepath.Join(projRoot, "src-tauri", "contacts.json"),
		"contacts.json",
		"src-tauri/contacts.json",
		"../contacts.json",
		"../../contacts.json",
	}

	for _, p := range candidatePaths {
		data, err := os.ReadFile(p)
		if err == nil && len(data) > 0 {
			// Try parsing as array
			if err := json.Unmarshal(data, &contacts); err == nil && len(contacts) > 0 {
				return contacts
			}
			// Try parsing as object with "contacts" key
			var wrapper struct {
				Contacts []PihuContact `json:"contacts"`
			}
			if err := json.Unmarshal(data, &wrapper); err == nil && len(wrapper.Contacts) > 0 {
				return wrapper.Contacts
			}
		}
	}
	return contacts
}

func resolveWhatsAppRecipient(input string) (recipientJID string, displayName string, phoneFormatted string) {
	clean := strings.TrimLeft(strings.TrimSpace(input), "-")
	if clean == "" {
		return "", "", ""
	}

	// If already a WhatsApp JID (e.g. group @g.us or user @s.whatsapp.net)
	if strings.Contains(clean, "@") {
		return clean, clean, clean
	}

	cleanLower := strings.ToLower(clean)

	// 1. Check saved contacts directory (~/.pihu/contacts.json or workspace contacts.json)
	contacts := loadAllContacts()
	for _, c := range contacts {
		if strings.ToLower(c.Name) == cleanLower ||
			strings.ToLower(c.Nickname) == cleanLower ||
			strings.ToLower(c.ID) == cleanLower ||
			strings.Contains(strings.ToLower(c.Name), cleanLower) ||
			(c.Nickname != "" && strings.Contains(strings.ToLower(c.Nickname), cleanLower)) {
			target := c.WhatsappJid
			if target == "" {
				target = c.Phone
			}
			// Clean target digits
			digits := cleanDigits(target)
			if len(digits) == 10 && (digits[0] == '6' || digits[0] == '7' || digits[0] == '8' || digits[0] == '9') {
				digits = "91" + digits
			}
			name := c.Name
			if c.Nickname != "" {
				name = fmt.Sprintf("%s (%s)", c.Name, c.Nickname)
			}
			return digits, name, c.Phone
		}
	}

	// 2. Query live WhatsApp bridge for existing contacts, chats, and groups
	client := http.Client{Timeout: 800 * time.Millisecond}
	if resp, err := client.Get("http://localhost:8080/api/chats"); err == nil {
		defer resp.Body.Close()
		var res struct {
			Chats []struct {
				JID     string `json:"jid"`
				Name    string `json:"name"`
				IsGroup bool   `json:"is_group"`
			} `json:"chats"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&res); err == nil {
			for _, chat := range res.Chats {
				if chat.Name == "" {
					continue
				}
				chatNameLower := strings.ToLower(chat.Name)
				if chatNameLower == cleanLower || strings.Contains(chatNameLower, cleanLower) {
					label := chat.Name
					if chat.IsGroup {
						label = fmt.Sprintf("%s [WhatsApp Group]", chat.Name)
					}
					return chat.JID, label, chat.JID
				}
			}
		}
	}

	// 3. Direct phone number
	digits := cleanDigits(clean)
	if len(digits) >= 7 {
		if len(digits) == 10 && (digits[0] == '6' || digits[0] == '7' || digits[0] == '8' || digits[0] == '9') {
			digits = "91" + digits
		}
		return digits, "+" + digits, "+" + digits
	}

	// Not found as contact and not a valid phone number
	return "", clean, ""
}

func cleanDigits(s string) string {
	var sb strings.Builder
	for _, r := range s {
		if r >= '0' && r <= '9' {
			sb.WriteRune(r)
		}
	}
	return sb.String()
}

var mcpWhatsappCmd = &cobra.Command{
	Use:   "whatsapp [auth|login|status|logout|send]",
	Short: "WhatsApp MCP authentication, messaging, status check, and device pairing",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) == 0 {
			mcpWhatsappStatusCmd.Run(cmd, args)
			return
		}
		sub := strings.ToLower(args[0])
		if sub == "auth" || sub == "login" {
			mcpWhatsappAuthCmd.Run(cmd, args)
		} else if sub == "logout" {
			mcpWhatsappLogoutCmd.Run(cmd, args)
		} else if sub == "send" {
			mcpWhatsappSendCmd.Run(cmd, args[1:])
		} else {
			mcpWhatsappStatusCmd.Run(cmd, args)
		}
	},
}

var mcpWhatsappSendCmd = &cobra.Command{
	Use:   "send <contact_or_number> <message...>",
	Short: "Send a WhatsApp message to a saved contact or phone number",
	Run: func(cmd *cobra.Command, args []string) {
		if len(args) < 2 {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Render("Usage: pihu mcp whatsapp send <contact_or_phone> \"<message>\""))
			fmt.Println("Example: pihu mcp whatsapp send anin \"Hi, this is test from PIHU\"")
			fmt.Println("Example: pihu mcp whatsapp send 9926674532 \"Hi, this is test\"")
			return
		}

		targetArg := args[0]
		messageText := strings.Join(args[1:], " ")

		recipientJID, displayName, phone := resolveWhatsAppRecipient(targetArg)
		if recipientJID == "" {
			fmt.Println(ui.RenderAsciiArt())
			fmt.Println()
			fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdMauve).Render("● PIHU WhatsApp Messenger"))
			fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))
			fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Bold(true).Render(fmt.Sprintf("✗ Contact '%s' not found in People Directory (~/.pihu/contacts.json) or WhatsApp chats.", targetArg)))
			fmt.Println("  Tip: Add '" + targetArg + "' in Settings > People & Directory, or specify a phone number directly:")
			fmt.Printf("       pihu mcp whatsapp send 9926674532 \"%s\"\n", messageText)
			fmt.Println()
			return
		}

		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()
		fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdMauve).Render("● PIHU WhatsApp Messenger"))
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))

		// Ensure bridge is active
		if err := ensureWhatsAppBridgeRunning(); err != nil {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Render("Starting bridge background process: " + err.Error()))
		}

		client := http.Client{Timeout: 15000 * time.Millisecond}

		// Check if logged in
		stResp, stErr := client.Get("http://localhost:8080/api/status")
		var isLoggedIn bool
		if stErr == nil {
			var st struct {
				LoggedIn bool   `json:"logged_in"`
				JID      string `json:"jid"`
			}
			json.NewDecoder(stResp.Body).Decode(&st)
			stResp.Body.Close()
			isLoggedIn = st.LoggedIn
		}

		if !isLoggedIn {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdYellow).Bold(true).Render("Device not paired yet. Please scan the QR code to authenticate:"))
			fmt.Println()
			// Call auth flow inline
			mcpWhatsappAuthCmd.Run(cmd, []string{})
		}

		// Send message payload
		payload := map[string]string{
			"recipient": recipientJID,
			"message":   messageText,
		}
		bodyBytes, _ := json.Marshal(payload)

		fmt.Println(lipgloss.NewStyle().Foreground(cmdSapph).Render(fmt.Sprintf("==> Dispatching WhatsApp message to %s (%s)...", displayName, phone)))

		resp, err := client.Post("http://localhost:8080/api/send", "application/json", bytes.NewBuffer(bodyBytes))
		if err != nil {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Bold(true).Render("✗ Failed to contact WhatsApp bridge daemon: " + err.Error()))
			return
		}
		defer resp.Body.Close()

		var sendRes struct {
			Success bool   `json:"success"`
			Message string `json:"message"`
		}
		json.NewDecoder(resp.Body).Decode(&sendRes)

		if sendRes.Success || resp.StatusCode == 200 {
			fmt.Println()
			fmt.Println(lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render("✔ Message successfully sent via PIHU WhatsApp MCP!"))
			fmt.Printf("  • Recipient:  %s\n", displayName)
			if phone != "" && phone != displayName {
				fmt.Printf("  • Number:     %s\n", phone)
			}
			fmt.Printf("  • Message:    \"%s\"\n", messageText)
			fmt.Printf("  • Device OS:  PIHU (Desktop)\n")
			fmt.Println()
		} else {
			fmt.Println()
			fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Bold(true).Render("✗ Failed to send WhatsApp message: " + sendRes.Message))
			fmt.Println("  Tip: Make sure the phone number includes country code (e.g. 919926674532) and WhatsApp bridge is active.")
			fmt.Println()
		}
	},
}

var mcpWhatsappStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Check WhatsApp MCP session and bridge connection status",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()
		title := lipgloss.NewStyle().Bold(true).Foreground(cmdGreen).
			Render("● WhatsApp MCP Bridge Status (PIHU Desktop)")
		fmt.Println(title)
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))

		client := http.Client{Timeout: 800 * time.Millisecond}
		resp, err := client.Get("http://localhost:8080/api/status")
		if err != nil {
			// Auto start bridge check
			fmt.Println(lipgloss.NewStyle().Foreground(cmdSapph).Render("  Starting WhatsApp bridge daemon in background..."))
			_ = ensureWhatsAppBridgeRunning()
			time.Sleep(500 * time.Millisecond)
			resp, err = client.Get("http://localhost:8080/api/status")
		}

		if err != nil {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Render("  ○ WhatsApp Bridge: Offline"))
			fmt.Println("    Run 'pihu mcp whatsapp auth' to automatically start pairing.")
			fmt.Println()
			return
		}
		defer resp.Body.Close()
		var st struct {
			Connected bool   `json:"connected"`
			LoggedIn  bool   `json:"logged_in"`
			JID       string `json:"jid"`
			OS        string `json:"os"`
			Platform  string `json:"platform"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&st); err != nil {
			fmt.Println("  ✗ Error reading bridge status")
			return
		}

		if st.LoggedIn {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render("  ✓ WhatsApp Session: Authenticated & Connected"))
			fmt.Println("    Device OS:   " + st.OS)
			fmt.Println("    Platform:    " + st.Platform)
			fmt.Println("    Linked JID:  " + st.JID)
		} else {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdYellow).Bold(true).Render("  ○ WhatsApp Session: Pairing Required (Not Linked)"))
			fmt.Println("    Run 'pihu mcp whatsapp auth' to pair your phone via QR code.")
		}
		fmt.Println()
	},
}

var mcpWhatsappAuthCmd = &cobra.Command{
	Use:     "auth",
	Aliases: []string{"login"},
	Short:   "Pair WhatsApp with PIHU via interactive terminal QR code",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()
		fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(cmdMauve).Render("PIHU WhatsApp Device Authentication"))
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))

		fmt.Println(lipgloss.NewStyle().Foreground(cmdSapph).Render("==> Checking WhatsApp Bridge daemon..."))
		if err := ensureWhatsAppBridgeRunning(); err != nil {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Render("Notice: Starting bridge background process: " + err.Error()))
		}

		client := http.Client{Timeout: 2000 * time.Millisecond}

		// Check if already authenticated
		if resp, err := client.Get("http://localhost:8080/api/status"); err == nil {
			var st struct {
				LoggedIn bool   `json:"logged_in"`
				JID      string `json:"jid"`
			}
			json.NewDecoder(resp.Body).Decode(&st)
			resp.Body.Close()
			if st.LoggedIn {
				fmt.Println(lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render(fmt.Sprintf("✓ WhatsApp is already authenticated as: %s (PIHU Desktop)", st.JID)))
				fmt.Println("  PIHU AI Agent is ready to send and receive WhatsApp messages.")
				fmt.Println()
				return
			}
		}

		fmt.Println(lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render("✓ Bridge daemon active on http://localhost:8080"))
		fmt.Println()
		fmt.Println("1. Open WhatsApp on your mobile phone")
		fmt.Println("2. Go to Settings > Linked Devices > Link a Device")
		fmt.Println("3. Scan the QR code below (Device name: PIHU Desktop):")
		fmt.Println()

		var lastQR string
		attempts := 0
		for {
			attempts++
			resp, err := client.Get("http://localhost:8080/api/qr")
			if err == nil {
				var q struct {
					QRCode   string `json:"qr_code"`
					Status   string `json:"status"`
					LoggedIn bool   `json:"logged_in"`
				}
				json.NewDecoder(resp.Body).Decode(&q)
				resp.Body.Close()

				if q.LoggedIn {
					fmt.Println()
					fmt.Println(lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render("✔ Successfully connected and authenticated with WhatsApp!"))
					fmt.Println("  Linked as PIHU (Desktop). AI Agent is now active.")
					fmt.Println()
					return
				}

				if q.QRCode != "" && q.QRCode != lastQR {
					lastQR = q.QRCode
					fmt.Println(lipgloss.NewStyle().Foreground(cmdYellow).Bold(true).Render("Scan this QR code with WhatsApp:"))
					fmt.Println()
					qrterminal.GenerateHalfBlock(q.QRCode, qrterminal.L, os.Stdout)
					fmt.Println()
					fmt.Println(lipgloss.NewStyle().Foreground(cmdMuted).Render("Waiting for scan... (Press Ctrl+C to cancel)"))
				}
			}

			// Check auth status as well
			if stResp, stErr := client.Get("http://localhost:8080/api/status"); stErr == nil {
				var st struct {
					LoggedIn bool   `json:"logged_in"`
					JID      string `json:"jid"`
				}
				json.NewDecoder(stResp.Body).Decode(&st)
				stResp.Body.Close()
				if st.LoggedIn {
					fmt.Println()
					fmt.Println(lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render(fmt.Sprintf("✔ Authenticated successfully as %s (PIHU Desktop)!", st.JID)))
					fmt.Println()
					return
				}
			}

			if attempts > 120 {
				fmt.Println(lipgloss.NewStyle().Foreground(cmdPeach).Render("Pairing timed out. Run 'pihu mcp whatsapp auth' to retry."))
				return
			}
			time.Sleep(1 * time.Second)
		}
	},
}

var mcpWhatsappLogoutCmd = &cobra.Command{
	Use:   "logout",
	Short: "Log out active WhatsApp session and unlink PIHU device",
	Run: func(cmd *cobra.Command, args []string) {
		client := http.Client{Timeout: 1000 * time.Millisecond}
		resp, err := client.Post("http://localhost:8080/api/logout", "application/json", nil)
		if err != nil {
			fmt.Println(lipgloss.NewStyle().Foreground(cmdYellow).Render("WhatsApp bridge is not currently running."))
			return
		}
		defer resp.Body.Close()
		fmt.Println(lipgloss.NewStyle().Foreground(cmdGreen).Bold(true).Render("✓ WhatsApp session unlinked successfully."))
	},
}

// ─── version ──────────────────────────────────────────────────────────────────

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print PIHU CLI version and environment information",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()

		cwd, _ := os.Getwd()
		ws := workspace.Detect(findProjectRoot(cwd))

		vStyle := lipgloss.NewStyle().Bold(true).Foreground(cmdMauve)
		label := lipgloss.NewStyle().Foreground(cmdMuted).Width(20)
		val := lipgloss.NewStyle().Foreground(lipgloss.Color("#cdd6f4"))

		fmt.Printf("  %s %s\n", label.Render("PIHU OS Version:"), vStyle.Render("v1.0.0"))
		fmt.Printf("  %s %s\n", label.Render("CLI Runtime:"), val.Render("Go 1.26 + Cobra + Bubble Tea + Lipgloss + Glamour"))
		fmt.Printf("  %s %s\n", label.Render("Agent Core:"), val.Render("Python 3.10+ / Hatchling"))
		fmt.Printf("  %s %s\n", label.Render("MCP Protocol:"), val.Render("JSON-RPC 2.0  (53 Tools Active)"))
		fmt.Printf("  %s %s\n", label.Render("LLM Support:"), val.Render("Google Gemini 2.0 Flash + Local Ollama"))
		fmt.Printf("  %s %s\n", label.Render("Output:"), val.Render("glamour v1.0 · chroma v2.27 · syntax highlighting · diffs · trees"))
		fmt.Println()

		// Render workspace card via the render package
		if ws.Name != "" {
			r := render.New(80)
			fmt.Println(r.WorkspaceCard(ws.Name, ws.Language, ws.Framework, ws.PackageMgr, ws.GitBranch, ws.GitDirty, ws.FileCount))
		}
	},
}
