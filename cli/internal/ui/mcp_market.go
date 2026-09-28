package ui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// MCPCatalogItem represents an MCP server available for installation.
type MCPCatalogItem struct {
	Name        string
	DisplayName string
	Category    string
	Description string
	InstallCmd  string
	Installed   bool
}

var CommunityMCPCatalog = []MCPCatalogItem{
	{
		Name:        "sqlite",
		DisplayName: "SQLite Database MCP",
		Category:    "Database",
		Description: "Query, introspect, and execute SQL across local SQLite databases",
		InstallCmd:  "pip install mcp-server-sqlite",
		Installed:   false,
	},
	{
		Name:        "postgres",
		DisplayName: "PostgreSQL Database MCP",
		Category:    "Database",
		Description: "Connect and manage PostgreSQL schemas, queries, and migrations",
		InstallCmd:  "pip install mcp-server-postgres",
		Installed:   false,
	},
	{
		Name:        "github",
		DisplayName: "GitHub Integration MCP",
		Category:    "Developer Tools",
		Description: "Create PRs, issues, read commits, workflows, and search code",
		InstallCmd:  "npx -y @modelcontextprotocol/server-github",
		Installed:   false,
	},
	{
		Name:        "docker",
		DisplayName: "Docker Engine MCP",
		Category:    "DevOps",
		Description: "Inspect, start, stop containers, view logs, and manage images",
		InstallCmd:  "pip install mcp-server-docker",
		Installed:   false,
	},
	{
		Name:        "puppeteer",
		DisplayName: "Puppeteer Web Automation MCP",
		Category:    "Web & Scraping",
		Description: "Headless browser automation, screenshots, and visual DOM inspection",
		InstallCmd:  "npx -y @modelcontextprotocol/server-puppeteer",
		Installed:   false,
	},
	{
		Name:        "fetch",
		DisplayName: "Universal Fetch & Scraper MCP",
		Category:    "Web & Scraping",
		Description: "Fetch and convert web pages into clean LLM-friendly markdown",
		InstallCmd:  "pip install mcp-server-fetch",
		Installed:   false,
	},
	{
		Name:        "brave-search",
		DisplayName: "Brave Web Search MCP",
		Category:    "Search",
		Description: "Privacy-focused real-time web search and index querying",
		InstallCmd:  "npx -y @modelcontextprotocol/server-brave-search",
		Installed:   false,
	},
	{
		Name:        "slack",
		DisplayName: "Slack Workspace MCP",
		Category:    "Productivity",
		Description: "Read channels, send messages, threads, and workspace notifications",
		InstallCmd:  "npx -y @modelcontextprotocol/server-slack",
		Installed:   false,
	},
}

// RenderMCPMarketModal renders the interactive MCP server browser and installer.
func RenderMCPMarketModal(
	catalog []MCPCatalogItem,
	selectedIndex int,
	filter string,
	w, h int,
) string {
	modalW := min(78, w-6)
	if modalW < 36 {
		modalW = 36
	}
	innerW := modalW - 4

	var rows []string

	header := lipgloss.NewStyle().Foreground(colGreen).Bold(true).
		Render("◇ MCP Directory & Marketplace (5 Connected · Community Catalog)")
	helpBar := lipgloss.NewStyle().Foreground(colSubtext).
		Render("Enter: View / Install  ·  Esc: Close  ·  Filter: " + filter)
	divider := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW))

	rows = append(rows, header, helpBar, divider)

	maxShow := 6
	start := 0
	if selectedIndex >= maxShow {
		start = selectedIndex - maxShow + 1
	}
	end := min(len(catalog), start+maxShow)

	for i := start; i < end; i++ {
		item := catalog[i]
		isSelected := (i == selectedIndex)

		pointer := "  "
		nameStyle := lipgloss.NewStyle().Foreground(colSky).Bold(true)
		catStyle := lipgloss.NewStyle().Foreground(colMuted)
		descStyle := lipgloss.NewStyle().Foreground(colSubtext)

		if isSelected {
			pointer = lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("› ")
			nameStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
			descStyle = lipgloss.NewStyle().Foreground(colText)
		}

		topLine := pointer + nameStyle.Render(item.DisplayName) + "  " + catStyle.Render("["+item.Category+"]")
		descLine := "    " + descStyle.Render(item.Description)
		installLine := "    " + lipgloss.NewStyle().Foreground(colYellow).Italic(true).Render("Install: "+item.InstallCmd)

		rows = append(rows, topLine, descLine, installLine, "")
	}

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colGreen).
		Background(colMantle).
		Padding(1, 2).
		Width(modalW).
		Render(strings.Join(rows, "\n"))
}
