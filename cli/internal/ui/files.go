package ui

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// FileItem represents a candidate file for the @ mention picker.
type FileItem struct {
	RelPath  string
	FileName string
	IsDir    bool
	SizeStr  string
	Icon     string
}

// ScanWorkspaceFiles searches files in rootDir, skipping build and cache artifacts.
func ScanWorkspaceFiles(rootDir string, maxResults int) []FileItem {
	var items []FileItem
	skipDirs := map[string]bool{
		".git":         true,
		"node_modules": true,
		".venv":        true,
		"venv":         true,
		"dist":         true,
		"build":        true,
		"target":       true,
		"__pycache__":  true,
		".pytest_cache":true,
		".pihu":        true,
		".next":        true,
	}

	filepath.Walk(rootDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(rootDir, path)
		if rel == "." {
			return nil
		}

		parts := strings.Split(rel, string(os.PathSeparator))
		for _, p := range parts {
			if skipDirs[p] {
				if info.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
		}

		if len(parts) > 5 {
			if info.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}

		if !info.IsDir() {
			sizeStr := formatFileSize(info.Size())
			icon := fileDevIcon(info.Name())
			items = append(items, FileItem{
				RelPath:  rel,
				FileName: info.Name(),
				IsDir:    false,
				SizeStr:  sizeStr,
				Icon:     icon,
			})
			if maxResults > 0 && len(items) >= maxResults {
				return fmt.Errorf("limit")
			}
		}
		return nil
	})

	return items
}

func formatFileSize(bytes int64) string {
	if bytes < 1024 {
		return fmt.Sprintf("%d B", bytes)
	}
	if bytes < 1024*1024 {
		return fmt.Sprintf("%.1f KB", float64(bytes)/1024)
	}
	return fmt.Sprintf("%.1f MB", float64(bytes)/(1024*1024))
}

// FilterFileItems returns files matching the query substring.
func FilterFileItems(items []FileItem, query string) []FileItem {
	if query == "" {
		return items
	}
	q := strings.ToLower(query)
	var matches []FileItem
	for _, item := range items {
		if strings.Contains(strings.ToLower(item.RelPath), q) || strings.Contains(strings.ToLower(item.FileName), q) {
			matches = append(matches, item)
		}
	}
	return matches
}

// RenderFilePickerModal renders a floating fuzzy file explorer for @ mentions.
func RenderFilePickerModal(
	files []FileItem,
	selectedIndex int,
	query string,
	w, h int,
) string {
	modalW := min(76, w-6)
	if modalW < 36 {
		modalW = 36
	}
	innerW := modalW - 4

	var rows []string

	// Header
	header := lipgloss.NewStyle().Foreground(colMauve).Bold(true).
		Render("◇ Select File to Mention (@) — Enter/Tab to insert, Esc to dismiss")
	searchBar := lipgloss.NewStyle().Foreground(colMuted).Render("Query: ") +
		lipgloss.NewStyle().Foreground(colSky).Bold(true).Render(query)
	divider := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW))

	rows = append(rows, header, searchBar, divider)

	if len(files) == 0 {
		rows = append(rows, lipgloss.NewStyle().Foreground(colMuted).Italic(true).
			Render("  No matching files in workspace"))
	} else {
		maxShow := 8
		start := 0
		if selectedIndex >= maxShow {
			start = selectedIndex - maxShow + 1
		}
		end := min(len(files), start+maxShow)

		for i := start; i < end; i++ {
			f := files[i]
			isSelected := (i == selectedIndex)

			pointer := "  "
			iconStyle := lipgloss.NewStyle().Foreground(colSky)
			pathStyle := lipgloss.NewStyle().Foreground(colText)
			sizeStyle := lipgloss.NewStyle().Foreground(colMuted)

			if isSelected {
				pointer = lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("› ")
				pathStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
				sizeStyle = lipgloss.NewStyle().Foreground(colSubtext)
			}

			pathStr := f.RelPath
			if len(pathStr) > innerW-18 {
				pathStr = "..." + pathStr[len(pathStr)-(innerW-21):]
			}

			row := fmt.Sprintf("%s%s %s",
				pointer,
				iconStyle.Render(f.Icon),
				pathStyle.Width(innerW-14).Render(pathStr),
			) + sizeStyle.Render(f.SizeStr)

			rows = append(rows, row)
		}
	}

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Background(colMantle).
		Padding(1, 2).
		Width(modalW).
		Render(strings.Join(rows, "\n"))
}
