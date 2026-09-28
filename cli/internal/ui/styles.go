package ui

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// Catppuccin Mocha Color Palette
	Mauve      = lipgloss.Color("#cba6f7")
	Lavender   = lipgloss.Color("#b4befe")
	Blue       = lipgloss.Color("#89b4fa")
	Sapphire   = lipgloss.Color("#74c7ec")
	Sky        = lipgloss.Color("#89dceb")
	Teal       = lipgloss.Color("#94e2d5")
	Green      = lipgloss.Color("#a6e3a1")
	Yellow     = lipgloss.Color("#f9e2af")
	Peach      = lipgloss.Color("#fab387")
	Maroon     = lipgloss.Color("#eba0ac")
	Red        = lipgloss.Color("#f38ba8")
	TextMain   = lipgloss.Color("#cdd6f4")
	TextSub    = lipgloss.Color("#a6adc8")
	TextMuted  = lipgloss.Color("#6c7086")
	Surface0   = lipgloss.Color("#313244")
	Base       = lipgloss.Color("#1e1e2e")
	Mantle     = lipgloss.Color("#181825")
	Crust      = lipgloss.Color("#11111b")

	// Prompt and Input Styles
	PromptPrefix = lipgloss.NewStyle().
			Bold(true).
			Foreground(Mauve).
			Render("pihu")

	PromptArrow = lipgloss.NewStyle().
			Bold(true).
			Foreground(Green).
			Render("❯ ")

	PromptContainer = lipgloss.NewStyle().
			MarginTop(1)

	// Status Icons
	SuccessIcon = lipgloss.NewStyle().
			Foreground(Green).
			Bold(true).
			SetString("✓")

	RunningIcon = lipgloss.NewStyle().
			Foreground(Yellow).
			Bold(true).
			SetString("⠋")

	ErrorIcon = lipgloss.NewStyle().
			Foreground(Red).
			Bold(true).
			SetString("✗")

	ArrowIcon = lipgloss.NewStyle().
			Foreground(Blue).
			SetString("→")

	ToolIcon = lipgloss.NewStyle().
			Foreground(Mauve).
			Bold(true).
			SetString("◇")

	ResultHeaderStyle = ResultHeader
	ResultCardStyle   = ResultBox

	// Tool Execution Card
	ToolCard = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("#45475a")).
			Background(Mantle).
			Padding(0, 1).
			MarginLeft(2).
			MarginTop(0).
			MarginBottom(1)

	ToolServerTag = lipgloss.NewStyle().
			Foreground(Mauve).
			Bold(true)

	ToolNameTag = lipgloss.NewStyle().
			Foreground(Blue).
			Bold(true)

	ToolOutputText = lipgloss.NewStyle().
			Foreground(TextSub)

	// Result Card
	ResultBox = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(Green).
			Padding(1, 2).
			MarginTop(1).
			MarginBottom(1).
			Foreground(TextMain)

	ResultHeader = lipgloss.NewStyle().
			Bold(true).
			Foreground(Green)

	// Timeline Badges & Categories
	TimelineCategory = lipgloss.NewStyle().
				Bold(true).
				Foreground(Blue).
				MarginTop(1)

	TimelineItem = lipgloss.NewStyle().
			MarginLeft(2).
			Foreground(TextMain)

	TimelineDetail = lipgloss.NewStyle().
			MarginLeft(6).
			Foreground(TextMuted).
			Italic(true)

	// Slash Commands Table
	TableHeader = lipgloss.NewStyle().
			Bold(true).
			Foreground(Mauve).
			Padding(0, 1)

	TableCellCmd = lipgloss.NewStyle().
			Bold(true).
			Foreground(Green).
			Padding(0, 1)

	TableCellDesc = lipgloss.NewStyle().
			Foreground(TextSub).
			Padding(0, 1)

	// General Box Styles
	HeaderStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(Mauve).
			Padding(0, 2).
			MarginBottom(1)

	TitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(Mauve)

	SubtitleStyle = lipgloss.NewStyle().
			Foreground(TextMuted)

	TaskLabelStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(Mauve)

	TaskValueStyle = lipgloss.NewStyle().
			Foreground(TextMain).
			Bold(true)

	FooterStyle = lipgloss.NewStyle().
			Foreground(TextMuted).
			MarginTop(1)

	FooterBadge = lipgloss.NewStyle().
			Background(Mauve).
			Foreground(Crust).
			Padding(0, 1).
			Bold(true)

	DividerStyle = lipgloss.NewStyle().
			Foreground(Surface0)
)
