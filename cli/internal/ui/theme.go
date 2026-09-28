package ui

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// ThemePalette holds all color tokens for the TUI.
type ThemePalette struct {
	Name        string
	DisplayName string
	Mauve       lipgloss.Color
	Blue        lipgloss.Color
	Green       lipgloss.Color
	Red         lipgloss.Color
	Yellow      lipgloss.Color
	Peach       lipgloss.Color
	Teal        lipgloss.Color
	Sky         lipgloss.Color
	Text        lipgloss.Color
	Subtext     lipgloss.Color
	Muted       lipgloss.Color
	Surf0       lipgloss.Color
	Surf1       lipgloss.Color
	Base        lipgloss.Color
	Mantle      lipgloss.Color
	Crust       lipgloss.Color
}

var (
	// Catppuccin Mocha (Default)
	ThemeCatppuccin = ThemePalette{
		Name:        "catppuccin",
		DisplayName: "Catppuccin Mocha",
		Mauve:       lipgloss.Color("#cba6f7"),
		Blue:        lipgloss.Color("#89b4fa"),
		Green:       lipgloss.Color("#a6e3a1"),
		Red:         lipgloss.Color("#f38ba8"),
		Yellow:      lipgloss.Color("#f9e2af"),
		Peach:       lipgloss.Color("#fab387"),
		Teal:        lipgloss.Color("#94e2d5"),
		Sky:         lipgloss.Color("#89dceb"),
		Text:        lipgloss.Color("#cdd6f4"),
		Subtext:     lipgloss.Color("#a6adc8"),
		Muted:       lipgloss.Color("#6c7086"),
		Surf0:       lipgloss.Color("#313244"),
		Surf1:       lipgloss.Color("#45475a"),
		Base:        lipgloss.Color("#1e1e2e"),
		Mantle:      lipgloss.Color("#181825"),
		Crust:       lipgloss.Color("#11111b"),
	}

	// Tokyo Night
	ThemeTokyoNight = ThemePalette{
		Name:        "tokyonight",
		DisplayName: "Tokyo Night",
		Mauve:       lipgloss.Color("#bb9af7"),
		Blue:        lipgloss.Color("#7aa2f7"),
		Green:       lipgloss.Color("#9ece6a"),
		Red:         lipgloss.Color("#f7768e"),
		Yellow:      lipgloss.Color("#e0af68"),
		Peach:       lipgloss.Color("#ff9e64"),
		Teal:        lipgloss.Color("#73daca"),
		Sky:         lipgloss.Color("#7dcfff"),
		Text:        lipgloss.Color("#c0caf5"),
		Subtext:     lipgloss.Color("#a9b1d6"),
		Muted:       lipgloss.Color("#565f89"),
		Surf0:       lipgloss.Color("#24283b"),
		Surf1:       lipgloss.Color("#414868"),
		Base:        lipgloss.Color("#1a1b26"),
		Mantle:      lipgloss.Color("#16161e"),
		Crust:       lipgloss.Color("#13141c"),
	}

	// Nord
	ThemeNord = ThemePalette{
		Name:        "nord",
		DisplayName: "Nordic Frost",
		Mauve:       lipgloss.Color("#b48ead"),
		Blue:        lipgloss.Color("#81a1c1"),
		Green:       lipgloss.Color("#a3be8c"),
		Red:         lipgloss.Color("#bf616a"),
		Yellow:      lipgloss.Color("#ebcb8b"),
		Peach:       lipgloss.Color("#d08770"),
		Teal:        lipgloss.Color("#8fbcbb"),
		Sky:         lipgloss.Color("#88c0d0"),
		Text:        lipgloss.Color("#eceff4"),
		Subtext:     lipgloss.Color("#e5e9f0"),
		Muted:       lipgloss.Color("#616e88"),
		Surf0:       lipgloss.Color("#3b4252"),
		Surf1:       lipgloss.Color("#4c566a"),
		Base:        lipgloss.Color("#2e3440"),
		Mantle:      lipgloss.Color("#272c36"),
		Crust:       lipgloss.Color("#1e222b"),
	}

	// Gruvbox Dark
	ThemeGruvbox = ThemePalette{
		Name:        "gruvbox",
		DisplayName: "Gruvbox Dark",
		Mauve:       lipgloss.Color("#d3869b"),
		Blue:        lipgloss.Color("#83a598"),
		Green:       lipgloss.Color("#b8bb26"),
		Red:         lipgloss.Color("#fb4934"),
		Yellow:      lipgloss.Color("#fabd2f"),
		Peach:       lipgloss.Color("#fe8019"),
		Teal:        lipgloss.Color("#8ec07c"),
		Sky:         lipgloss.Color("#83a598"),
		Text:        lipgloss.Color("#ebdbb2"),
		Subtext:     lipgloss.Color("#d5c4a1"),
		Muted:       lipgloss.Color("#928374"),
		Surf0:       lipgloss.Color("#3c3836"),
		Surf1:       lipgloss.Color("#504945"),
		Base:        lipgloss.Color("#282828"),
		Mantle:      lipgloss.Color("#1d2021"),
		Crust:       lipgloss.Color("#141617"),
	}

	// Dracula
	ThemeDracula = ThemePalette{
		Name:        "dracula",
		DisplayName: "Dracula Vamp",
		Mauve:       lipgloss.Color("#bd93f9"),
		Blue:        lipgloss.Color("#8be9fd"),
		Green:       lipgloss.Color("#50fa7b"),
		Red:         lipgloss.Color("#ff5555"),
		Yellow:      lipgloss.Color("#f1fa8c"),
		Peach:       lipgloss.Color("#ffb86c"),
		Teal:        lipgloss.Color("#8be9fd"),
		Sky:         lipgloss.Color("#6ee7b7"),
		Text:        lipgloss.Color("#f8f8f2"),
		Subtext:     lipgloss.Color("#bfbfbf"),
		Muted:       lipgloss.Color("#6272a4"),
		Surf0:       lipgloss.Color("#44475a"),
		Surf1:       lipgloss.Color("#6272a4"),
		Base:        lipgloss.Color("#282a36"),
		Mantle:      lipgloss.Color("#21222c"),
		Crust:       lipgloss.Color("#191a21"),
	}

	// One Dark
	ThemeOneDark = ThemePalette{
		Name:        "onedark",
		DisplayName: "One Dark Pro",
		Mauve:       lipgloss.Color("#c678dd"),
		Blue:        lipgloss.Color("#61afef"),
		Green:       lipgloss.Color("#98c379"),
		Red:         lipgloss.Color("#e06c75"),
		Yellow:      lipgloss.Color("#e5c07b"),
		Peach:       lipgloss.Color("#d19a66"),
		Teal:        lipgloss.Color("#56b6c2"),
		Sky:         lipgloss.Color("#4fa6ed"),
		Text:        lipgloss.Color("#abb2bf"),
		Subtext:     lipgloss.Color("#828997"),
		Muted:       lipgloss.Color("#5c6370"),
		Surf0:       lipgloss.Color("#2c313a"),
		Surf1:       lipgloss.Color("#3e4451"),
		Base:        lipgloss.Color("#21252b"),
		Mantle:      lipgloss.Color("#1e2227"),
		Crust:       lipgloss.Color("#181a1f"),
	}

	AvailableThemes = []ThemePalette{
		ThemeCatppuccin,
		ThemeTokyoNight,
		ThemeNord,
		ThemeGruvbox,
		ThemeDracula,
		ThemeOneDark,
	}

	// Current active theme
	CurrentTheme = ThemeCatppuccin

	// Background transparency mode (true by default for macOS blur)
	TransparentBackground = true
)

// SetTheme sets the active theme palette by name.
func SetTheme(name string) (ThemePalette, bool) {
	name = strings.ToLower(strings.TrimSpace(name))
	for _, t := range AvailableThemes {
		if strings.EqualFold(t.Name, name) || strings.EqualFold(strings.ReplaceAll(t.Name, " ", ""), name) {
			CurrentTheme = t
			applyThemeGlobals(t)
			saveThemeConfig(t.Name, TransparentBackground)
			return t, true
		}
	}
	return CurrentTheme, false
}

// ToggleTransparency flips background transparency between transparent blur and solid base.
func ToggleTransparency() bool {
	TransparentBackground = !TransparentBackground
	saveThemeConfig(CurrentTheme.Name, TransparentBackground)
	return TransparentBackground
}

func applyThemeGlobals(t ThemePalette) {
	colMauve = t.Mauve
	colBlue = t.Blue
	colGreen = t.Green
	colRed = t.Red
	colYellow = t.Yellow
	colPeach = t.Peach
	colTeal = t.Teal
	colSky = t.Sky
	colText = t.Text
	colSubtext = t.Subtext
	colMuted = t.Muted
	colSurf0 = t.Surf0
	colSurf1 = t.Surf1
	colBase = t.Base
	colMantle = t.Mantle
	colCrust = t.Crust
}

func saveThemeConfig(themeName string, transparent bool) {
	home, err := os.UserHomeDir()
	if err != nil {
		return
	}
	cfgDir := filepath.Join(home, ".pihu")
	os.MkdirAll(cfgDir, 0755)
	cfgPath := filepath.Join(cfgDir, "theme.json")

	data, err := json.MarshalIndent(map[string]interface{}{
		"theme":       themeName,
		"transparent": transparent,
	}, "", "  ")
	if err == nil {
		os.WriteFile(cfgPath, data, 0644)
	}
}

// LoadThemeConfig restores user's saved theme from ~/.pihu/theme.json
func LoadThemeConfig() {
	home, err := os.UserHomeDir()
	if err != nil {
		return
	}
	cfgPath := filepath.Join(home, ".pihu", "theme.json")
	if data, err := os.ReadFile(cfgPath); err == nil {
		var cfg struct {
			Theme       string `json:"theme"`
			Transparent bool   `json:"transparent"`
		}
		if json.Unmarshal(data, &cfg) == nil {
			if cfg.Theme != "" {
				SetTheme(cfg.Theme)
			}
			TransparentBackground = cfg.Transparent
		}
	}
}
