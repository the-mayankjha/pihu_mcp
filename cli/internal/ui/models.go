package ui

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

// ModelItem represents an available LLM model (Cloud or Local).
type ModelItem struct {
	Provider string // "gemini" or "ollama"
	Name     string // e.g. "gemini-2.0-flash", "qwen3:4b"
	Tagline  string
	IsLocal  bool
	SizeInfo string
}

// DiscoverGeminiKey finds the active Gemini API key from env or .env files.
func DiscoverGeminiKey() string {
	for _, envVar := range []string{
		"PIHU_GEMINI_API_KEY",
		"PIHU_GEMINI_API_KEY2",
		"PIHU_GEMINI_API_KEY3",
		"GEMINI_API_KEY",
		"GOOGLE_API_KEY",
	} {
		if val := strings.TrimSpace(os.Getenv(envVar)); val != "" {
			return val
		}
	}

	if pool := os.Getenv("VITE_GEMINI_API_KEYS"); pool != "" {
		parts := strings.Split(pool, ",")
		if len(parts) > 0 && strings.TrimSpace(parts[0]) != "" {
			return strings.TrimSpace(parts[0])
		}
	}

	// Try reading .env files
	cwd, _ := os.Getwd()
	envPaths := []string{
		filepath.Join(cwd, ".env"),
		filepath.Join(cwd, "..", ".env"),
		filepath.Join(cwd, "..", "..", ".env"),
	}
	if home, err := os.UserHomeDir(); err == nil {
		envPaths = append(envPaths,
			filepath.Join(home, ".pihu-os", ".env"),
			filepath.Join(home, ".pihu", ".env"),
		)
	}

	for _, p := range envPaths {
		if f, err := os.Open(p); err == nil {
			scanner := bufio.NewScanner(f)
			for scanner.Scan() {
				line := strings.TrimSpace(scanner.Text())
				if strings.HasPrefix(line, "#") || !strings.Contains(line, "=") {
					continue
				}
				parts := strings.SplitN(line, "=", 2)
				k := strings.TrimSpace(parts[0])
				v := strings.Trim(strings.TrimSpace(parts[1]), "\"'")
				if (strings.Contains(k, "GEMINI_API_KEY") || strings.Contains(k, "GEMINI_API_KEYS")) && v != "" {
					f.Close()
					if strings.Contains(v, ",") {
						return strings.TrimSpace(strings.Split(v, ",")[0])
					}
					return v
				}
			}
			f.Close()
		}
	}

	return ""
}

// FetchAvailableModels dynamically discovers models from Google Gemini API and Local Ollama.
func FetchAvailableModels() []ModelItem {
	var models []ModelItem

	// ── 1. Dynamic Cloud Models from Google Gemini API ───────────────────────
	apiKey := DiscoverGeminiKey()
	geminiLoaded := false

	if apiKey != "" {
		client := http.Client{Timeout: 1200 * time.Millisecond}
		url := fmt.Sprintf("https://generativelanguage.googleapis.com/v1beta/models?key=%s", apiKey)
		resp, err := client.Get(url)
		if err == nil && resp.StatusCode == 200 {
			defer resp.Body.Close()
			var data struct {
				Models []struct {
					Name                       string   `json:"name"`
					DisplayName                string   `json:"displayName"`
					Description                string   `json:"description"`
					SupportedGenerationMethods []string `json:"supportedGenerationMethods"`
				} `json:"models"`
			}
			if err := json.NewDecoder(resp.Body).Decode(&data); err == nil && len(data.Models) > 0 {
				skipKeywords := []string{"preview", "tts", "image", "transcribe", "embedding", "nano", "banana", "omni", "gemma", "custom"}
				for _, m := range data.Models {
					name := strings.TrimPrefix(m.Name, "models/")
					if !strings.HasPrefix(name, "gemini") {
						continue
					}
					// Must support generateContent
					hasGen := false
					for _, meth := range m.SupportedGenerationMethods {
						if meth == "generateContent" {
							hasGen = true
							break
						}
					}
					if !hasGen {
						continue
					}
					nameLower := strings.ToLower(name)
					skip := false
					for _, kw := range skipKeywords {
						if strings.Contains(nameLower, kw) {
							skip = true
							break
						}
					}
					if skip {
						continue
					}

					tagline := m.DisplayName
					if tagline == "" {
						tagline = m.Description
					}
					if len(tagline) > 42 {
						tagline = tagline[:39] + "..."
					}
					models = append(models, ModelItem{
						Provider: "gemini",
						Name:     name,
						Tagline:  tagline,
						IsLocal:  false,
						SizeInfo: "Cloud",
					})
				}
				if len(models) > 0 {
					geminiLoaded = true
				}
			}
		}
	}

	// Gemini fallback catalog if offline / key expired
	if !geminiLoaded {
		models = append(models,
			ModelItem{
				Provider: "gemini",
				Name:     "gemini-2.0-flash",
				Tagline:  "Recommended · Fast, Multimodal, Real-Time",
				IsLocal:  false,
				SizeInfo: "Cloud",
			},
			ModelItem{
				Provider: "gemini",
				Name:     "gemini-2.0-flash-lite",
				Tagline:  "Ultra Low Latency & High Speed",
				IsLocal:  false,
				SizeInfo: "Cloud",
			},
			ModelItem{
				Provider: "gemini",
				Name:     "gemini-2.0-pro-exp-02-05",
				Tagline:  "Heavy Reasoning, Architecture & Coding",
				IsLocal:  false,
				SizeInfo: "Cloud",
			},
			ModelItem{
				Provider: "gemini",
				Name:     "gemini-1.5-flash",
				Tagline:  "High Throughput & Rapid Task Loop",
				IsLocal:  false,
				SizeInfo: "Cloud",
			},
			ModelItem{
				Provider: "gemini",
				Name:     "gemini-1.5-pro",
				Tagline:  "2M Token Context & Deep Repository Analysis",
				IsLocal:  false,
				SizeInfo: "Cloud",
			},
		)
	}

	// ── 2. Dynamic Local Models from Ollama Daemon ────────────────────────────
	client := http.Client{Timeout: 600 * time.Millisecond}
	resp, err := client.Get("http://localhost:11434/api/tags")
	ollamaLoaded := false

	if err == nil && resp.StatusCode == 200 {
		defer resp.Body.Close()
		var data struct {
			Models []struct {
				Name    string `json:"name"`
				Size    int64  `json:"size"`
				Details struct {
					ParameterSize string `json:"parameter_size"`
					Family        string `json:"family"`
				} `json:"details"`
			} `json:"models"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&data); err == nil && len(data.Models) > 0 {
			for _, m := range data.Models {
				sizeGB := fmt.Sprintf("%.1f GB", float64(m.Size)/(1024*1024*1024))
				tagline := m.Details.Family
				if m.Details.ParameterSize != "" {
					tagline = m.Details.ParameterSize + " " + m.Details.Family
				}
				if tagline == "" {
					tagline = "Local Ollama Weights"
				}
				models = append(models, ModelItem{
					Provider: "ollama",
					Name:     m.Name,
					Tagline:  tagline,
					IsLocal:  true,
					SizeInfo: sizeGB,
				})
			}
			ollamaLoaded = true
		}
	}

	// Ollama fallback catalog if daemon not running
	if !ollamaLoaded {
		models = append(models,
			ModelItem{
				Provider: "ollama",
				Name:     "qwen3:4b",
				Tagline:  "Local Fast Coding Agent (Default)",
				IsLocal:  true,
				SizeInfo: "2.4 GB",
			},
			ModelItem{
				Provider: "ollama",
				Name:     "llama3.2:latest",
				Tagline:  "Local Meta Llama 3.2 3B",
				IsLocal:  true,
				SizeInfo: "2.0 GB",
			},
			ModelItem{
				Provider: "ollama",
				Name:     "deepseek-r1:8b",
				Tagline:  "Local DeepSeek Reasoning Model",
				IsLocal:  true,
				SizeInfo: "4.9 GB",
			},
			ModelItem{
				Provider: "ollama",
				Name:     "mistral:latest",
				Tagline:  "Local Mistral 7B General Assistant",
				IsLocal:  true,
				SizeInfo: "4.1 GB",
			},
		)
	}

	return models
}

// RenderModelSelector renders the floating model selection modal.
func RenderModelSelector(
	models []ModelItem,
	filter string,
	selectedIndex int,
	currentModel string,
	filterInputView string,
	w, h int,
) string {
	modalW := min(76, w-6)
	if modalW < 40 {
		modalW = 40
	}

	// Filter models by search query
	var filtered []ModelItem
	q := strings.ToLower(strings.TrimSpace(filter))
	for _, m := range models {
		if q == "" || strings.Contains(strings.ToLower(m.Name), q) ||
			strings.Contains(strings.ToLower(m.Provider), q) ||
			strings.Contains(strings.ToLower(m.Tagline), q) {
			filtered = append(filtered, m)
		}
	}

	if len(filtered) == 0 {
		filtered = models
	}

	if selectedIndex < 0 {
		selectedIndex = 0
	}
	if selectedIndex >= len(filtered) {
		selectedIndex = len(filtered) - 1
	}

	var sb strings.Builder
	title := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("◇ Select LLM Model (Dynamic Cloud + Local)")
	sb.WriteString(title + "\n\n")

	// Search input
	searchBar := lipgloss.NewStyle().Foreground(colMuted).Render("Search: ") + filterInputView
	sb.WriteString(searchBar + "\n")
	sb.WriteString(lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", modalW-4)) + "\n")

	// Model rows
	lastProvider := ""
	for i, m := range filtered {
		if m.Provider != lastProvider {
			lastProvider = m.Provider
			var sectionName string
			var sectionColor lipgloss.Color
			if m.IsLocal {
				sectionName = "Local Models (Ollama)"
				sectionColor = colBlue
			} else {
				sectionName = "Cloud Models (Google Gemini)"
				sectionColor = colGreen
			}
			secHeader := lipgloss.NewStyle().Foreground(sectionColor).Bold(true).Render(sectionName)
			sb.WriteString(secHeader + "\n")
		}

		isSelected := i == selectedIndex
		isCurrent := m.Name == currentModel

		cursor := "  "
		nameStyle := lipgloss.NewStyle().Foreground(colText)
		tagStyle := lipgloss.NewStyle().Foreground(colMuted)

		if isSelected {
			cursor = lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("❯ ")
			nameStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
			tagStyle = lipgloss.NewStyle().Foreground(colSubtext)
		}

		check := ""
		if isCurrent {
			check = lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render(" [active]")
		}

		nameCol := nameStyle.Width(26).Render(m.Name)
		tagCol := tagStyle.Render(m.Tagline)
		sizeCol := lipgloss.NewStyle().Foreground(colMuted).Render(" (" + m.SizeInfo + ")")

		line := fmt.Sprintf("%s%s %s%s%s", cursor, nameCol, tagCol, sizeCol, check)
		sb.WriteString(line + "\n")
	}

	sb.WriteString("\n" + lipgloss.NewStyle().Foreground(colMuted).Render("↑/↓ Navigate  •  Enter Select  •  Esc Cancel"))

	return lipgloss.NewStyle().
		Width(modalW).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Padding(1, 2).
		Render(sb.String())
}
