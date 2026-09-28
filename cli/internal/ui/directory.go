package ui

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// DirEntry represents a folder item in the directory browser.
type DirEntry struct {
	Name     string
	FullPath string
	IsDir    bool
	IsParent bool
}

// ListDirectoryFolders returns subdirectories and parent entry for path.
func ListDirectoryFolders(dirPath string) ([]DirEntry, error) {
	absPath, err := filepath.Abs(dirPath)
	if err != nil {
		absPath = dirPath
	}

	var entries []DirEntry

	// Parent directory
	parent := filepath.Dir(absPath)
	if parent != absPath {
		entries = append(entries, DirEntry{
			Name:     ".. (Parent Directory)",
			FullPath: parent,
			IsDir:    true,
			IsParent: true,
		})
	}

	files, err := os.ReadDir(absPath)
	if err != nil {
		return entries, err
	}

	for _, f := range files {
		if f.IsDir() && !strings.HasPrefix(f.Name(), ".") {
			entries = append(entries, DirEntry{
				Name:     f.Name() + "/",
				FullPath: filepath.Join(absPath, f.Name()),
				IsDir:    true,
				IsParent: false,
			})
		}
	}

	return entries, nil
}

// RenderDirBrowserModal renders the interactive /cd directory selector modal.
func RenderDirBrowserModal(
	currentPath string,
	entries []DirEntry,
	selectedIndex int,
	w, h int,
) string {
	modalW := min(76, w-6)
	if modalW < 36 {
		modalW = 36
	}
	innerW := modalW - 4

	var rows []string

	header := lipgloss.NewStyle().Foreground(colBlue).Bold(true).
		Render("◇ Change Project Directory (/cd)")
	pathBadge := lipgloss.NewStyle().Foreground(colMuted).Render("Current: ") +
		lipgloss.NewStyle().Foreground(colSky).Bold(true).Render(truncatePath(currentPath, innerW-12))
	helpBar := lipgloss.NewStyle().Foreground(colSubtext).
		Render("Enter: Navigate folder  ·  Space / c: Select current  ·  Esc: Cancel")
	divider := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW))

	rows = append(rows, header, pathBadge, helpBar, divider)

	// Action row: Select Current Directory
	isSelectCurrentSelected := (selectedIndex == -1)
	selectCurPrefix := "  "
	selectCurStyle := lipgloss.NewStyle().Foreground(colGreen).Bold(true)
	if isSelectCurrentSelected {
		selectCurPrefix = "› "
		selectCurStyle = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
	}
	rows = append(rows, selectCurPrefix+selectCurStyle.Render("[✔ Select This Folder as Active Workspace]"), "")

	if len(entries) == 0 {
		rows = append(rows, lipgloss.NewStyle().Foreground(colMuted).Italic(true).
			Render("  (No subdirectories)"))
	} else {
		maxShow := 7
		start := 0
		if selectedIndex >= maxShow {
			start = selectedIndex - maxShow + 1
		}
		if start < 0 {
			start = 0
		}
		end := min(len(entries), start+maxShow)

		for i := start; i < end; i++ {
			e := entries[i]
			isSelected := (i == selectedIndex)

			pointer := "  "
			icon := "📁 "
			if e.IsParent {
				icon = "⬆ "
			}
			style := lipgloss.NewStyle().Foreground(colText)
			if isSelected {
				pointer = lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("› ")
				style = lipgloss.NewStyle().Foreground(colMauve).Bold(true)
			}

			nameStr := e.Name
			if len(nameStr) > innerW-8 {
				nameStr = nameStr[:innerW-11] + "..."
			}

			rows = append(rows, fmt.Sprintf("%s%s%s", pointer, icon, style.Render(nameStr)))
		}
	}

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colBlue).
		Background(colMantle).
		Padding(1, 2).
		Width(modalW).
		Render(strings.Join(rows, "\n"))
}
