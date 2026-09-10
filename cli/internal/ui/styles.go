package ui

import (
	"github.com/charmbracelet/lipgloss"
)

var (
	// Modern Vibrant Color Palette
	Cyan     = lipgloss.Color("#00E5FF")
	Purple   = lipgloss.Color("#A855F7")
	Emerald  = lipgloss.Color("#10B981")
	Amber    = lipgloss.Color("#F59E0B")
	Crimson  = lipgloss.Color("#EF4444")
	TextMain = lipgloss.Color("#F3F4F6")
	TextMuted= lipgloss.Color("#9CA3AF")
	BgCard   = lipgloss.Color("#181825")
	BorderColor = lipgloss.Color("#3B0764")

	// Header Box
	HeaderStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(Purple).
			Padding(0, 2).
			MarginBottom(1)

	TitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(Cyan)

	SubtitleStyle = lipgloss.NewStyle().
			Foreground(TextMuted)

	// Task Box
	TaskLabelStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(Purple).
			MarginBottom(0)

	TaskValueStyle = lipgloss.NewStyle().
			Foreground(TextMain).
			MarginLeft(2).
			Bold(true)

	// Timeline Badges & Categories
	SuccessIcon = lipgloss.NewStyle().
			Foreground(Emerald).
			Bold(true)

	RunningIcon = lipgloss.NewStyle().
			Foreground(Amber).
			Bold(true)

	ErrorIcon = lipgloss.NewStyle().
			Foreground(Crimson).
			Bold(true)

	ArrowIcon = lipgloss.NewStyle().
			Foreground(Cyan)

	TimelineCategory = lipgloss.NewStyle().
				Bold(true).
				Foreground(Cyan).
				MarginTop(1)

	TimelineItem = lipgloss.NewStyle().
			MarginLeft(2).
			Foreground(TextMain)

	TimelineDetail = lipgloss.NewStyle().
			MarginLeft(6).
			Foreground(TextMuted).
			Italic(true)

	// Result Card Box
	ResultHeaderStyle = lipgloss.NewStyle().
				Bold(true).
				Foreground(Emerald)

	ResultCardStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(Emerald).
			Padding(1, 2).
			MarginTop(1).
			MarginBottom(1).
			Foreground(TextMain)

	// Footer Pill
	FooterStyle = lipgloss.NewStyle().
			Foreground(TextMuted).
			MarginTop(1)

	FooterBadge = lipgloss.NewStyle().
			Background(Purple).
			Foreground(TextMain).
			Padding(0, 1).
			Bold(true)

	DividerStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#374151"))
)
