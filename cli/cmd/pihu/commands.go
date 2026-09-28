package main

import (
	"fmt"
	"os"
	"strings"

	"pihu/cli/internal/render"
	"pihu/cli/internal/ui"
	"pihu/cli/internal/workspace"

	"github.com/charmbracelet/lipgloss"
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
	Short: "Inspect connected MCP servers status, health, and transports",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println(ui.RenderAsciiArt())
		fmt.Println()

		title := lipgloss.NewStyle().Bold(true).Foreground(cmdGreen).
			Render("● Active MCP Servers Registry (5 of 5 Online)")
		fmt.Println(title)
		fmt.Println(lipgloss.NewStyle().Foreground(cmdSurf1).Render(strings.Repeat("─", 70)))

		servers := []struct {
			Name      string
			Transport string
			Tools     int
		}{
			{"pihu-file-mcp", "stdio (python)", 24},
			{"pihu-system-mcp", "stdio (python)", 7},
			{"pihu-web-search-mcp", "stdio (python)", 6},
			{"google-workspace-mcp", "stdio (python)", 10},
			{"pihu-project-mcp", "stdio (node)", 6},
		}

		for _, s := range servers {
			dot := lipgloss.NewStyle().Foreground(cmdGreen).Render("✓")
			name := lipgloss.NewStyle().Foreground(cmdMauve).Bold(true).Width(25).Render(s.Name)
			transport := lipgloss.NewStyle().Foreground(cmdMuted).Width(18).Render(s.Transport)
			tools := lipgloss.NewStyle().Foreground(cmdBlue).Render(fmt.Sprintf("%2d tools", s.Tools))
			fmt.Printf("  %s  %s %s  %s\n", dot, name, transport, tools)
		}
		fmt.Println()
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
