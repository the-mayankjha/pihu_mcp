package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

const AsciiLogo = `
  ██████╗ ██╗██╗  ██╗██╗   ██╗
  ██╔══██╗██║██║  ██║██║   ██║
  ██████╔╝██║███████║██║   ██║
  ██╔═══╝ ██║██╔══██║██║   ██║
  ██║     ██║██║  ██║╚██████╔╝
  ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ `

var (
	// Gradient colors for ASCII art lines
	gradientColors = []string{
		"#cba6f7", // Mauve
		"#b4befe", // Lavender
		"#89b4fa", // Blue
		"#74c7ec", // Sapphire
		"#89dceb", // Sky
		"#a6e3a1", // Green
	}
)

// RenderAsciiArt returns the colored ASCII logo
func RenderAsciiArt() string {
	lines := strings.Split(strings.Trim(AsciiLogo, "\n"), "\n")
	var rendered []string
	for i, line := range lines {
		colorIdx := i % len(gradientColors)
		style := lipgloss.NewStyle().Foreground(lipgloss.Color(gradientColors[colorIdx])).Bold(true)
		rendered = append(rendered, style.Render(line))
	}
	return strings.Join(rendered, "\n")
}

// RenderBanner displays the complete startup banner with ASCII art and system status
func RenderBanner(provider, model string, serverCount, toolCount int, workspace string) string {
	logo := RenderAsciiArt()

	tagline := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#9399b2")).
		Italic(true).
		Render("Personalized Intelligent Human Utility • Desktop & Code Agent")

	metaStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#cdd6f4"))
	accentStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#cba6f7")).Bold(true)
	greenStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#a6e3a1")).Bold(true)
	blueStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#89b4fa")).Bold(true)

	if provider == "" {
		provider = "gemini"
	}
	if model == "" {
		if provider == "gemini" {
			model = "gemini-2.0-flash"
		} else {
			model = "qwen3:4b"
		}
	}
	if serverCount == 0 {
		serverCount = 5
	}
	if toolCount == 0 {
		toolCount = 53
	}

	info := fmt.Sprintf(
		"  %s %s (%s)  │  %s %s (%s)  │  %s %s",
		metaStyle.Render("Engine:"),
		accentStyle.Render(provider),
		blueStyle.Render(model),
		metaStyle.Render("MCP:"),
		greenStyle.Render(fmt.Sprintf("%d servers", serverCount)),
		greenStyle.Render(fmt.Sprintf("%d tools", toolCount)),
		metaStyle.Render("Directory:"),
		lipgloss.NewStyle().Foreground(lipgloss.Color("#f9e2af")).Render(truncatePath(workspace, 25)),
	)

	helpTip := lipgloss.NewStyle().
		Foreground(lipgloss.Color("#6c7086")).
		Render("  Type a prompt to execute, or /help for slash commands (/tools, /mcp, /model, /clear, /exit)")

	boxContent := fmt.Sprintf("%s\n\n  %s\n\n%s\n%s", logo, tagline, info, helpTip)

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("#cba6f7")).
		Padding(0, 1).
		MarginBottom(1).
		Render(boxContent)
}

func truncatePath(p string, maxLen int) string {
	if len(p) <= maxLen {
		return p
	}
	return "..." + p[len(p)-(maxLen-3):]
}
