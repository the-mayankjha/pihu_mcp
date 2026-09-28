package ui

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// KeyItem represents an API key entry in the token pool.
type KeyItem struct {
	Key      string
	Masked   string
	Source   string
	IsActive bool
	IsCustom bool
}

func maskKey(k string) string {
	if len(k) <= 10 {
		return k
	}
	return k[:6] + "..." + k[len(k)-4:]
}

// DiscoverAllGeminiKeys finds all Gemini API keys from environment and config files.
// DiscoverAllGeminiKeys finds all Gemini API keys from environment and config files.
func DiscoverAllGeminiKeys(activeKey string) []KeyItem {
	var keys []KeyItem
	seen := make(map[string]bool)

	addKey := func(k, src string) {
		k = strings.TrimSpace(k)
		if k == "" || seen[k] || len(k) < 15 {
			return
		}
		seen[k] = true
		keys = append(keys, KeyItem{
			Key:      k,
			Masked:   maskKey(k),
			Source:   src,
			IsActive: (k == activeKey),
			IsCustom: false,
		})
	}

	// 1. Scan all environment variables matching *GEMINI* or *PIHU*KEY*
	for _, envStr := range os.Environ() {
		parts := strings.SplitN(envStr, "=", 2)
		if len(parts) != 2 {
			continue
		}
		kUpper := strings.ToUpper(parts[0])
		v := strings.TrimSpace(parts[1])
		if (strings.Contains(kUpper, "GEMINI") && strings.Contains(kUpper, "KEY")) ||
			(strings.Contains(kUpper, "GEMINI") && strings.Contains(kUpper, "TOKEN")) ||
			(strings.Contains(kUpper, "PIHU") && strings.Contains(kUpper, "KEY")) ||
			(strings.Contains(kUpper, "GOOGLE") && strings.Contains(kUpper, "KEY")) {
			if strings.Contains(v, ",") {
				for idx, part := range strings.Split(v, ",") {
					addKey(part, fmt.Sprintf("env: %s[%d]", parts[0], idx+1))
				}
			} else {
				addKey(v, "env: "+parts[0])
			}
		}
	}

	// Direct common variables
	for _, envVar := range []string{
		"PIHU_GEMINI_API_KEY",
		"PIHU_GEMINI_API_KEY2",
		"PIHU_GEMINI_API_KEY3",
		"PIHU_GEMINI_API_KEY4",
		"PIHU_GEMINI_KEY_1",
		"PIHU_GEMINI_KEY_2",
		"PIHU_GEMINI_KEY_3",
		"GEMINI_API_KEY",
		"GEMINI_API_KEY_1",
		"GEMINI_API_KEY_2",
		"GOOGLE_API_KEY",
	} {
		if val := strings.TrimSpace(os.Getenv(envVar)); val != "" {
			addKey(val, "env: "+envVar)
		}
	}

	if pool := os.Getenv("VITE_GEMINI_API_KEYS"); pool != "" {
		for i, part := range strings.Split(pool, ",") {
			addKey(part, fmt.Sprintf("env: VITE_GEMINI_API_KEYS[%d]", i+1))
		}
	}

	// 2. Local & Global .env files
	cwd, _ := os.Getwd()
	envPaths := []struct {
		path  string
		label string
	}{
		{filepath.Join(cwd, ".env"), ".env"},
		{filepath.Join(cwd, "..", ".env"), "../.env"},
		{filepath.Join(cwd, "..", "..", ".env"), "../../.env"},
	}

	if home, err := os.UserHomeDir(); err == nil {
		envPaths = append(envPaths,
			struct {
				path  string
				label string
			}{filepath.Join(home, ".pihu-os", ".env"), "~/.pihu-os/.env"},
			struct {
				path  string
				label string
			}{filepath.Join(home, ".pihu", ".env"), "~/.pihu/.env"},
		)
	}

	for _, ep := range envPaths {
		if f, err := os.Open(ep.path); err == nil {
			scanner := bufio.NewScanner(f)
			for scanner.Scan() {
				line := strings.TrimSpace(scanner.Text())
				if strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
					continue
				}
				parts := strings.SplitN(line, "=", 2)
				k := strings.TrimSpace(parts[0])
				kUpper := strings.ToUpper(k)
				v := strings.Trim(strings.TrimSpace(parts[1]), "\"'")
				if (strings.Contains(kUpper, "GEMINI") && (strings.Contains(kUpper, "KEY") || strings.Contains(kUpper, "TOKEN"))) ||
					(strings.Contains(kUpper, "PIHU") && strings.Contains(kUpper, "KEY")) ||
					(strings.Contains(kUpper, "GOOGLE") && strings.Contains(kUpper, "KEY")) {
					if strings.Contains(v, ",") {
						for idx, subK := range strings.Split(v, ",") {
							addKey(subK, fmt.Sprintf("%s (%s[%d])", ep.label, k, idx+1))
						}
					} else {
						addKey(v, fmt.Sprintf("%s (%s)", ep.label, k))
					}
				}
			}
			f.Close()
		}
	}

	// If no key was marked active but we have keys, mark the first one
	hasActive := false
	for _, ki := range keys {
		if ki.IsActive {
			hasActive = true
			break
		}
	}
	if !hasActive && len(keys) > 0 {
		keys[0].IsActive = true
	}

	// Always add the "+ Add New Key" action at the end
	keys = append(keys, KeyItem{
		Key:      "",
		Masked:   "+ Add New Gemini API Key",
		Source:   "Configure new token in .env",
		IsActive: false,
		IsCustom: true,
	})

	return keys
}

// SaveGeminiKey writes or updates a Gemini API key into the local .env file and sets environment variables.
func SaveGeminiKey(name, key string) (string, error) {
	key = strings.TrimSpace(key)
	if key == "" {
		return "", fmt.Errorf("API key cannot be empty")
	}

	name = strings.TrimSpace(name)
	if name == "" {
		name = "PIHU_GEMINI_API_KEY"
	}

	os.Setenv(name, key)
	os.Setenv("PIHU_GEMINI_API_KEY", key)
	os.Setenv("GEMINI_API_KEY", key)

	cwd, err := os.Getwd()
	if err != nil {
		cwd = "."
	}
	envPath := filepath.Join(cwd, ".env")

	var lines []string
	found := false
	if f, err := os.Open(envPath); err == nil {
		scanner := bufio.NewScanner(f)
		for scanner.Scan() {
			l := scanner.Text()
			if strings.HasPrefix(strings.TrimSpace(l), name+"=") {
				lines = append(lines, fmt.Sprintf("%s=%s", name, key))
				found = true
			} else {
				lines = append(lines, l)
			}
		}
		f.Close()
	}

	if !found {
		lines = append(lines, fmt.Sprintf("%s=%s", name, key))
	}

	err = os.WriteFile(envPath, []byte(strings.Join(lines, "\n")+"\n"), 0644)
	if err != nil {
		return envPath, err
	}

	return envPath, nil
}

// RenderKeySelector renders the floating token selector modal.
func RenderKeySelector(
	keys []KeyItem,
	selectedIndex int,
	activeKey string,
	w, h int,
) string {
	modalW := min(76, w-6)
	if modalW < 44 {
		modalW = 44
	}

	if selectedIndex < 0 {
		selectedIndex = 0
	}
	if selectedIndex >= len(keys) {
		selectedIndex = len(keys) - 1
	}

	var sb strings.Builder
	title := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("◇ PIHU Token Protocol — Gemini API Keys")
	sb.WriteString(title + "\n")

	poolCount := len(keys) - 1
	if poolCount < 0 {
		poolCount = 0
	}
	subtitle := lipgloss.NewStyle().Foreground(colMuted).Render(
		fmt.Sprintf("%d token(s) configured in rotation pool · Select active key", poolCount),
	)
	sb.WriteString(subtitle + "\n")
	sb.WriteString(lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", modalW-4)) + "\n\n")

	for i, k := range keys {
		isSelected := (i == selectedIndex)
		isCurrent := k.IsActive || (k.Key != "" && k.Key == activeKey)

		cursor := "  "
		nameStyle := lipgloss.NewStyle().Foreground(colText)
		srcStyle := lipgloss.NewStyle().Foreground(colMuted)

		if isSelected {
			cursor = lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("❯ ")
			if k.IsCustom {
				nameStyle = lipgloss.NewStyle().Foreground(colYellow).Bold(true)
			} else {
				nameStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
			}
			srcStyle = lipgloss.NewStyle().Foreground(colSubtext)
		} else if k.IsCustom {
			nameStyle = lipgloss.NewStyle().Foreground(colSky)
		}

		check := ""
		if isCurrent && !k.IsCustom {
			check = lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render(" [active]")
		}

		if k.IsCustom {
			line := fmt.Sprintf("%s%s  %s", cursor, nameStyle.Render(k.Masked), srcStyle.Render("("+k.Source+")"))
			sb.WriteString(line + "\n")
		} else {
			idxBadge := lipgloss.NewStyle().Foreground(colMuted).Render(fmt.Sprintf("[%d] ", i+1))
			keyCol := nameStyle.Width(22).Render(k.Masked)
			srcCol := srcStyle.Render(k.Source)
			line := fmt.Sprintf("%s%s%s %s%s", cursor, idxBadge, keyCol, srcCol, check)
			sb.WriteString(line + "\n")
		}
	}

	sb.WriteString("\n" + lipgloss.NewStyle().Foreground(colMuted).Render("↑/↓ Navigate  •  Enter Select Active Key  •  Esc Close"))

	return lipgloss.NewStyle().
		Width(modalW).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Padding(1, 2).
		Render(sb.String())
}

// RenderKeyInputModal renders the input dialog for adding a new key.
func RenderKeyInputModal(inputView string, w, h int) string {
	modalW := min(68, w-6)
	if modalW < 40 {
		modalW = 40
	}

	var sb strings.Builder
	title := lipgloss.NewStyle().Foreground(colYellow).Bold(true).Render("◇ Add Gemini API Key to Pool")
	sb.WriteString(title + "\n\n")

	hint := lipgloss.NewStyle().Foreground(colSubtext).Render(
		"Enter your Google Gemini API key (starts with AIzaSy...):",
	)
	sb.WriteString(hint + "\n\n")

	sb.WriteString(inputView + "\n\n")
	sb.WriteString(lipgloss.NewStyle().Foreground(colMuted).Render("Enter Save & Activate  •  Esc Cancel"))

	return lipgloss.NewStyle().
		Width(modalW).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colYellow).
		Padding(1, 2).
		Render(sb.String())
}
