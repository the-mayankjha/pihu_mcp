package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// CommandSuggestion describes a slash command or argument completion.
type CommandSuggestion struct {
	Command string // e.g. "/model"
	Syntax  string // e.g. "/model [name]"
	Desc    string // e.g. "Switch active LLM model"
	Args    []string // suggestions for arguments
}

var SlashCommands = []CommandSuggestion{
	{
		Command: "/model",
		Syntax:  "/model [name]",
		Desc:    "Switch active LLM model (Gemini Cloud or Ollama Local)",
		Args:    []string{"gemini-2.0-flash", "gemini-2.5-flash", "gemini-3.7-flash", "qwen3:4b", "gemma3:4b"},
	},
	{
		Command: "/key",
		Syntax:  "/key [name] [token]",
		Desc:    "View, switch, or configure Gemini API tokens",
		Args:    []string{"PIHU_GEMINI_KEY_1", "PIHU_GEMINI_KEY_2", "PIHU_GEMINI_KEY_3"},
	},
	{
		Command: "/theme",
		Syntax:  "/theme [name|bg]",
		Desc:    "Switch theme or toggle transparency (catppuccin, tokyonight, nord, gruvbox, dracula, onedark, bg)",
		Args:    []string{"catppuccin", "tokyonight", "nord", "gruvbox", "dracula", "onedark", "bg"},
	},
	{
		Command: "/cd",
		Syntax:  "/cd [path]",
		Desc:    "Interactive directory browser or switch project workspace",
		Args:    []string{"..", "~"},
	},
	{
		Command: "/mcp",
		Syntax:  "/mcp [search|install|list]",
		Desc:    "Connected MCP server status or browse & install new MCPs",
		Args:    []string{"list", "search", "install", "sqlite", "postgres", "github", "puppeteer", "docker", "fetch"},
	},
	{
		Command: "/tools",
		Syntax:  "/tools",
		Desc:    "List all 53 active Model Context Protocol tools",
		Args:    nil,
	},
	{
		Command: "/provider",
		Syntax:  "/provider [gemini|ollama]",
		Desc:    "Toggle between cloud Gemini and local Ollama",
		Args:    []string{"gemini", "ollama"},
	},
	{
		Command: "/workspace",
		Syntax:  "/workspace",
		Desc:    "Display workspace detection, framework & git status",
		Args:    nil,
	},
	{
		Command: "/clear",
		Syntax:  "/clear",
		Desc:    "Clear conversation history",
		Args:    nil,
	},
	{
		Command: "/help",
		Syntax:  "/help",
		Desc:    "Display command reference and shortcuts",
		Args:    nil,
	},
	{
		Command: "/exit",
		Syntax:  "/exit",
		Desc:    "Exit PIHU REPL",
		Args:    nil,
	},
}

// GetCommandSuggestions returns matching commands or argument completions based on the input text.
func GetCommandSuggestions(input string) []CommandSuggestion {
	input = strings.TrimSpace(input)
	if !strings.HasPrefix(input, "/") {
		return nil
	}

	parts := strings.Fields(input)
	cmdPart := parts[0]

	// 1. If typing command itself: "/mod" -> matches "/model"
	if len(parts) == 1 && !strings.HasSuffix(input, " ") {
		var matches []CommandSuggestion
		for _, c := range SlashCommands {
			if strings.HasPrefix(c.Command, cmdPart) {
				matches = append(matches, c)
			}
		}
		return matches
	}

	// 2. If typing arguments: "/theme t" -> suggest "tokyonight"
	for _, c := range SlashCommands {
		if c.Command == cmdPart {
			argPrefix := ""
			if len(parts) > 1 {
				argPrefix = parts[len(parts)-1]
			}
			var argMatches []string
			for _, arg := range c.Args {
				if argPrefix == "" || strings.HasPrefix(strings.ToLower(arg), strings.ToLower(argPrefix)) {
					argMatches = append(argMatches, arg)
				}
			}
			if len(argMatches) > 0 {
				var res []CommandSuggestion
				for _, am := range argMatches {
					res = append(res, CommandSuggestion{
						Command: fmt.Sprintf("%s %s", c.Command, am),
						Syntax:  fmt.Sprintf("%s %s", c.Command, am),
						Desc:    c.Desc,
					})
				}
				return res
			}
			return []CommandSuggestion{c}
		}
	}

	return nil
}

// RenderSuggestionBox renders an interactive floating suggestion popup above the input field.
func RenderSuggestionBox(suggestions []CommandSuggestion, selectedIdx int, width int) string {
	if len(suggestions) == 0 {
		return ""
	}

	boxW := min(74, width-4)
	if boxW < 30 {
		boxW = 30
	}

	var rows []string
	header := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("◇ Suggestions (Tab to complete)")
	rows = append(rows, header, lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", boxW-4)))

	maxShow := min(6, len(suggestions))
	for i := 0; i < maxShow; i++ {
		s := suggestions[i]
		isSelected := (i == selectedIdx)

		pointer := "  "
		cmdStyle := lipgloss.NewStyle().Foreground(colGreen).Bold(true)
		descStyle := lipgloss.NewStyle().Foreground(colSubtext)

		if isSelected {
			pointer = lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("› ")
			cmdStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
			descStyle = lipgloss.NewStyle().Foreground(colText)
		}

		cmdStr := cmdStyle.Width(22).Render(s.Syntax)
		descStr := descStyle.Render(s.Desc)
		if len(descStr) > boxW-28 {
			descStr = descStr[:boxW-31] + "..."
		}

		rows = append(rows, pointer+cmdStr+" "+descStr)
	}

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Background(colMantle).
		Padding(0, 1).
		Width(boxW).
		Render(strings.Join(rows, "\n"))
}
