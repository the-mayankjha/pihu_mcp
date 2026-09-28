// Package render provides rich terminal output:
// markdown, syntax-highlighted code blocks, directory trees, diffs.
// Uses glamour (goldmark + chroma) under the hood.
package render

import (
	"bytes"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/alecthomas/chroma/v2/quick"
	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/glamour/ansi"
	"github.com/charmbracelet/lipgloss"
)

// ─── Catppuccin Mocha colours (shared) ───────────────────────────────────────

var (
	colMauve   = lipgloss.Color("#cba6f7")
	colBlue    = lipgloss.Color("#89b4fa")
	colGreen   = lipgloss.Color("#a6e3a1")
	colRed     = lipgloss.Color("#f38ba8")
	colYellow  = lipgloss.Color("#f9e2af")
	colPeach   = lipgloss.Color("#fab387")
	colTeal    = lipgloss.Color("#94e2d5")
	colSky     = lipgloss.Color("#89dceb")
	colText    = lipgloss.Color("#cdd6f4")
	colSubtext = lipgloss.Color("#a6adc8")
	colMuted   = lipgloss.Color("#6c7086")
	colSurf0   = lipgloss.Color("#313244")
	colSurf1   = lipgloss.Color("#45475a")
	colBase    = lipgloss.Color("#1e1e2e")
	colMantle  = lipgloss.Color("#181825")
	colCrust   = lipgloss.Color("#11111b")
)

// ─── Renderer ────────────────────────────────────────────────────────────────

// Renderer holds a configured glamour instance and renders rich content.
type Renderer struct {
	width   int
	glamour *glamour.TermRenderer
}

// New creates a Renderer for the given terminal width.
func New(width int) *Renderer {
	if width <= 0 {
		width = 100
	}
	r := &Renderer{width: width}
	r.glamour = newGlamour(width)
	return r
}

// Resize updates the renderer width.
func (r *Renderer) Resize(width int) {
	r.width = width
	r.glamour = newGlamour(width)
}

// ─── Markdown ────────────────────────────────────────────────────────────────

// Markdown renders markdown text, extracting code blocks to display them with
// syntax highlighting, line numbers, and clean rounded card boundaries.
func (r *Renderer) Markdown(md string) string {
	if strings.TrimSpace(md) == "" {
		return ""
	}

	if !strings.Contains(md, "```") {
		if r.glamour == nil {
			return lipgloss.NewStyle().Foreground(colText).Render(md)
		}
		out, err := r.glamour.Render(md)
		if err != nil {
			return lipgloss.NewStyle().Foreground(colText).Render(md)
		}
		return strings.TrimRight(out, "\n")
	}

	var resultParts []string
	lines := strings.Split(md, "\n")
	var proseBuffer []string
	inCodeBlock := false
	var codeBuffer []string
	var codeLang string
	var lastHeading string

	for i := 0; i < len(lines); i++ {
		line := lines[i]
		trimmed := strings.TrimSpace(line)

		if strings.HasPrefix(trimmed, "```") {
			if !inCodeBlock {
				if len(proseBuffer) > 0 {
					proseText := strings.Join(proseBuffer, "\n")
					if r.glamour != nil {
						if renderedProse, err := r.glamour.Render(proseText); err == nil && strings.TrimSpace(renderedProse) != "" {
							resultParts = append(resultParts, strings.TrimRight(renderedProse, "\n"))
						} else {
							resultParts = append(resultParts, proseText)
						}
					} else {
						resultParts = append(resultParts, proseText)
					}
					proseBuffer = nil
				}

				inCodeBlock = true
				codeBuffer = nil
				codeLang = strings.TrimPrefix(trimmed, "```")
				codeLang = strings.TrimSpace(codeLang)
			} else {
				inCodeBlock = false
				codeContent := strings.Join(codeBuffer, "\n")
				renderedCard := r.RenderCodeCard(codeLang, lastHeading, codeContent)
				resultParts = append(resultParts, renderedCard)
				codeBuffer = nil
				codeLang = ""
				lastHeading = ""
			}
			continue
		}

		if inCodeBlock {
			codeBuffer = append(codeBuffer, line)
		} else {
			if strings.HasPrefix(trimmed, "#") {
				lastHeading = trimmed
			}
			proseBuffer = append(proseBuffer, line)
		}
	}

	if inCodeBlock && len(codeBuffer) > 0 {
		codeContent := strings.Join(codeBuffer, "\n")
		renderedCard := r.RenderCodeCard(codeLang, lastHeading, codeContent)
		resultParts = append(resultParts, renderedCard)
	} else if len(proseBuffer) > 0 {
		proseText := strings.Join(proseBuffer, "\n")
		if r.glamour != nil {
			if renderedProse, err := r.glamour.Render(proseText); err == nil && strings.TrimSpace(renderedProse) != "" {
				resultParts = append(resultParts, strings.TrimRight(renderedProse, "\n"))
			} else {
				resultParts = append(resultParts, proseText)
			}
		} else {
			resultParts = append(resultParts, proseText)
		}
	}

	return strings.Join(resultParts, "\n\n")
}

// ─── Code Card Renderer with Line Numbers and Boundaries ───────────────────────

func (r *Renderer) RenderCodeCard(lang, heading, code string) string {
	code = strings.TrimRight(code, "\n")
	if code == "" {
		return ""
	}

	boxW := r.width - 4
	if boxW < 40 {
		boxW = 40
	}
	innerW := boxW - 4
	if innerW < 30 {
		innerW = 30
	}

	normLang := strings.ToLower(strings.TrimSpace(lang))
	headingLower := strings.ToLower(heading)

	isOutput := false
	if normLang == "output" || normLang == "terminal" || normLang == "console" || normLang == "stdout" ||
		strings.Contains(headingLower, "output") || strings.Contains(headingLower, "result") || strings.Contains(headingLower, "terminal") {
		isOutput = true
	}

	// 1. Output Block (Terminal Output Boundary)
	if isOutput {
		header := lipgloss.NewStyle().Foreground(colSky).Bold(true).Render("◇ Output")
		divider := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW))

		var outLines []string
		for _, l := range strings.Split(code, "\n") {
			outLines = append(outLines, lipgloss.NewStyle().Foreground(colText).Render(l))
		}

		cardContent := header + "\n" + divider + "\n" + strings.Join(outLines, "\n")
		return lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(colSky).
			Padding(0, 1).
			Width(boxW).
			Render(cardContent)
	}

	// 2. Source Code Block (Syntax Highlighted + Line Numbers + Card Boundary)
	if normLang == "" {
		if strings.Contains(headingLower, ".py") {
			normLang = "python"
		} else if strings.Contains(headingLower, ".go") {
			normLang = "go"
		} else if strings.Contains(headingLower, ".rs") {
			normLang = "rust"
		} else if strings.Contains(headingLower, ".ts") {
			normLang = "typescript"
		} else if strings.Contains(headingLower, ".js") {
			normLang = "javascript"
		} else if strings.Contains(headingLower, ".sh") || strings.Contains(headingLower, ".bash") {
			normLang = "bash"
		} else if strings.Contains(headingLower, ".json") {
			normLang = "json"
		} else {
			normLang = "text"
		}
	}

	filename := ""
	if start := strings.Index(heading, "("); start != -1 {
		if end := strings.Index(heading[start:], ")"); end != -1 {
			filename = strings.TrimSpace(heading[start+1 : start+end])
		}
	}

	var highlightedBuf bytes.Buffer
	err := quick.Highlight(&highlightedBuf, code, normLang, "terminal256", "catppuccin-mocha")
	highlightedCode := code
	if err == nil && highlightedBuf.Len() > 0 {
		highlightedCode = highlightedBuf.String()
	}

	codeLines := strings.Split(highlightedCode, "\n")
	lineCount := len(codeLines)

	var numberedLines []string
	for i, l := range codeLines {
		num := lipgloss.NewStyle().Foreground(colMuted).Width(3).Align(lipgloss.Right).Render(fmt.Sprintf("%d", i+1))
		sep := lipgloss.NewStyle().Foreground(colSurf1).Render(" │ ")
		numberedLines = append(numberedLines, num+sep+l)
	}

	icon := "◈ "
	if filename != "" {
		icon = fileDevIcon(filename)
	} else {
		icon = fileDevIcon("file." + normLang)
	}

	langBadge := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render(langLabel(normLang))
	fileBadge := ""
	if filename != "" {
		fileBadge = "  " + lipgloss.NewStyle().Foreground(colText).Bold(true).Render(filename)
	}
	countBadge := lipgloss.NewStyle().Foreground(colMuted).Render(fmt.Sprintf("  (%d lines)", lineCount))

	headerBar := icon + langBadge + fileBadge + countBadge
	divider := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW))

	cardContent := headerBar + "\n" + divider + "\n" + strings.Join(numberedLines, "\n")
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Padding(0, 1).
		Width(boxW).
		Render(cardContent)
}

// CodeBlock renders a standalone code block with language label and line numbers.
func (r *Renderer) CodeBlock(lang, code string) string {
	return r.RenderCodeCard(lang, "", code)
}

func fileDevIcon(filename string) string {
	ext := strings.ToLower(filepath.Ext(filename))
	switch ext {
	case ".py":
		return lipgloss.NewStyle().Foreground(colYellow).Render("◈ ")
	case ".go":
		return lipgloss.NewStyle().Foreground(colSky).Render("◈ ")
	case ".ts", ".tsx":
		return lipgloss.NewStyle().Foreground(colBlue).Render("◈ ")
	case ".js", ".jsx":
		return lipgloss.NewStyle().Foreground(colYellow).Render("◈ ")
	case ".rs":
		return lipgloss.NewStyle().Foreground(colPeach).Render("◈ ")
	case ".json", ".yaml", ".toml", ".env":
		return lipgloss.NewStyle().Foreground(colMauve).Render("◈ ")
	case ".md":
		return lipgloss.NewStyle().Foreground(colTeal).Render("◈ ")
	default:
		return lipgloss.NewStyle().Foreground(colSubtext).Render("◈ ")
	}
}

// ─── Diff ────────────────────────────────────────────────────────────────────

// DiffBlock renders a unified diff with +/- coloring and a file path header.
func (r *Renderer) DiffBlock(path, before, after string) string {
	hunks := makeDiffHunks(before, after)

	var sb strings.Builder

	// File header bar
	fileLabel := lipgloss.NewStyle().
		Background(colSurf0).
		Foreground(colBlue).
		Bold(true).
		Padding(0, 1).
		Render("● " + path)

	ext := strings.TrimPrefix(filepath.Ext(path), ".")
	langLabel2 := langLabel(ext)
	langTag := lipgloss.NewStyle().
		Background(colSurf1).
		Foreground(colMuted).
		Padding(0, 1).
		Render(langLabel2)

	headerLine := fileLabel + "  " + langTag
	sb.WriteString(headerLine + "\n\n")

	// Diff hunks
	addStyle := lipgloss.NewStyle().Foreground(colGreen).Bold(false)
	delStyle := lipgloss.NewStyle().Foreground(colRed).Bold(false)
	ctxStyle := lipgloss.NewStyle().Foreground(colMuted)
	atStyle := lipgloss.NewStyle().Foreground(colMauve).Bold(true)

	for _, h := range hunks {
		sb.WriteString(atStyle.Render(fmt.Sprintf("@@ -%d +%d @@\n", h.beforeLine, h.afterLine)))
		for _, l := range h.lines {
			switch {
			case strings.HasPrefix(l, "+"):
				sb.WriteString("  " + addStyle.Render(l) + "\n")
			case strings.HasPrefix(l, "-"):
				sb.WriteString("  " + delStyle.Render(l) + "\n")
			default:
				sb.WriteString("  " + ctxStyle.Render(l) + "\n")
			}
		}
		sb.WriteString("\n")
	}

	// Stat footer
	added, removed := countDiffStats(hunks)
	stat := lipgloss.JoinHorizontal(lipgloss.Left,
		lipgloss.NewStyle().Foreground(colGreen).Render(fmt.Sprintf("+%d", added)),
		"  ",
		lipgloss.NewStyle().Foreground(colRed).Render(fmt.Sprintf("-%d", removed)),
	)
	sb.WriteString("  " + stat + "\n")

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colSurf1).
		Background(colBase).
		Width(r.width - 4).
		PaddingLeft(1).
		Render(sb.String())
}

// ─── Directory Tree ───────────────────────────────────────────────────────────

// TreeEntry is one node in a directory tree.
type TreeEntry struct {
	Name     string
	IsDir    bool
	Children []TreeEntry
	Modified bool // highlight in yellow
	New      bool // highlight in green
}

// Tree renders a directory tree with box-drawing characters and color coding.
func (r *Renderer) Tree(root string, entries []TreeEntry) string {
	var sb strings.Builder

	// Root label
	rootLabel := lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render("◎ " + root)
	sb.WriteString(rootLabel + "\n")

	renderEntries(&sb, entries, "")

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colSurf1).
		Background(colBase).
		PaddingLeft(1).
		PaddingRight(1).
		Render(sb.String())
}

func renderEntries(sb *strings.Builder, entries []TreeEntry, prefix string) {
	for i, e := range entries {
		isLast := i == len(entries)-1
		connector := "├── "
		childPrefix := prefix + "│   "
		if isLast {
			connector = "└── "
			childPrefix = prefix + "    "
		}

		line := prefix + connector

		if e.IsDir {
			label := lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render(e.Name + "/")
			sb.WriteString(line + label + "\n")
		} else {
			var style lipgloss.Style
			switch {
			case e.New:
				style = lipgloss.NewStyle().Foreground(colGreen)
			case e.Modified:
				style = lipgloss.NewStyle().Foreground(colYellow)
			default:
				style = lipgloss.NewStyle().Foreground(colText)
			}
			// extension badge
			ext := filepath.Ext(e.Name)
			extBadge := ""
			if ext != "" {
				extBadge = "  " + lipgloss.NewStyle().Foreground(colMuted).Render(ext)
			}
			sb.WriteString(line + style.Render(e.Name) + extBadge + "\n")
		}

		if len(e.Children) > 0 {
			renderEntries(sb, e.Children, childPrefix)
		}
	}
}

// ─── Approval Box ────────────────────────────────────────────────────────────

// ApprovalBox renders the permission request UI.
type ApprovalRisk int

const (
	ApprovalSafe      ApprovalRisk = iota
	ApprovalModerate
	ApprovalDangerous
)

func (r *Renderer) ApprovalBox(command, reason string, risk ApprovalRisk) string {
	riskColor := colGreen
	riskLabel := "SAFE"
	switch risk {
	case ApprovalModerate:
		riskColor = colYellow
		riskLabel = "MODERATE"
	case ApprovalDangerous:
		riskColor = colRed
		riskLabel = "DANGEROUS"
	}

	riskBadge := lipgloss.NewStyle().
		Background(riskColor).
		Foreground(colCrust).
		Bold(true).
		Padding(0, 1).
		Render(riskLabel)

	title := lipgloss.NewStyle().Foreground(colMauve).Bold(true).
		Render("◉ Permission Required")

	cmd := lipgloss.NewStyle().
		Background(colSurf0).
		Foreground(colText).
		Padding(0, 2).
		Bold(true).
		Render("$ " + command)

	reasonLine := lipgloss.NewStyle().Foreground(colSubtext).Render(reason)

	opts := "\n" +
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("[A]") +
		lipgloss.NewStyle().Foreground(colSubtext).Render(" Allow once   ") +
		lipgloss.NewStyle().Foreground(colYellow).Bold(true).Render("[S]") +
		lipgloss.NewStyle().Foreground(colSubtext).Render(" Allow session   ") +
		lipgloss.NewStyle().Foreground(colRed).Bold(true).Render("[D]") +
		lipgloss.NewStyle().Foreground(colSubtext).Render(" Deny")

	inner := lipgloss.JoinVertical(lipgloss.Left,
		lipgloss.JoinHorizontal(lipgloss.Center, title, "  ", riskBadge),
		"",
		cmd,
		"",
		reasonLine,
		opts,
	)

	return lipgloss.NewStyle().
		Border(lipgloss.ThickBorder()).
		BorderForeground(riskColor).
		Padding(1, 2).
		Width(min(r.width-4, 72)).
		Render(inner)
}

// ─── Tool Step ───────────────────────────────────────────────────────────────

// ToolStep renders a single tool call line in the agent trace.
func (r *Renderer) ToolStep(icon, server, name, status, duration, preview string) string {
	var statusColor lipgloss.Color
	var statusIcon string
	switch status {
	case "done":
		statusColor = colGreen
		statusIcon = "✓"
	case "running":
		statusColor = colYellow
		statusIcon = "⠋"
	case "error":
		statusColor = colRed
		statusIcon = "✗"
	default:
		statusColor = colMuted
		statusIcon = "·"
	}

	dot := lipgloss.NewStyle().Foreground(statusColor).Bold(true).Render(statusIcon)
	serverTag := lipgloss.NewStyle().Foreground(colMauve).Render(server)
	toolName := lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render(name)
	dur := ""
	if duration != "" {
		dur = lipgloss.NewStyle().Foreground(colMuted).Render("  " + duration)
	}
	prev := ""
	if preview != "" {
		p := preview
		if len(p) > 60 {
			p = p[:57] + "..."
		}
		prev = "\n    " + lipgloss.NewStyle().Foreground(colMuted).Italic(true).Render(p)
	}

	return fmt.Sprintf("  %s  %s  %s  %s%s%s", dot, serverTag, toolName, icon, dur, prev)
}

// ─── Plan Box ────────────────────────────────────────────────────────────────

// PlanBox renders the numbered plan before execution.
func (r *Renderer) PlanBox(steps []string) string {
	var sb strings.Builder
	sb.WriteString(lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("◇ Plan") + "\n\n")
	for i, s := range steps {
		num := lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render(fmt.Sprintf("%d.", i+1))
		text := lipgloss.NewStyle().Foreground(colText).Render(s)
		sb.WriteString(fmt.Sprintf("  %s  %s\n", num, text))
	}
	sb.WriteString("\n")
	sb.WriteString(
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("[Y]") +
			lipgloss.NewStyle().Foreground(colSubtext).Render(" Apply this plan   ") +
			lipgloss.NewStyle().Foreground(colRed).Bold(true).Render("[N]") +
			lipgloss.NewStyle().Foreground(colSubtext).Render(" Cancel"),
	)

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Padding(1, 2).
		Width(min(r.width-4, 72)).
		Render(sb.String())
}

// ─── Command Output ───────────────────────────────────────────────────────────

// ShellOutput renders terminal command output.
func (r *Renderer) ShellOutput(command, output string) string {
	cmdLine := lipgloss.NewStyle().
		Foreground(colGreen).Bold(true).Render("$ " + command)

	lines := strings.Split(output, "\n")
	var styled []string
	for _, l := range lines {
		var s string
		switch {
		case strings.Contains(strings.ToLower(l), "error") || strings.Contains(strings.ToLower(l), "fail"):
			s = lipgloss.NewStyle().Foreground(colRed).Render(l)
		case strings.Contains(strings.ToLower(l), "pass") || strings.Contains(strings.ToLower(l), "ok") || strings.Contains(l, "✓"):
			s = lipgloss.NewStyle().Foreground(colGreen).Render(l)
		case strings.HasPrefix(l, "  ") || strings.HasPrefix(l, "\t"):
			s = lipgloss.NewStyle().Foreground(colSubtext).Render(l)
		default:
			s = lipgloss.NewStyle().Foreground(colText).Render(l)
		}
		styled = append(styled, s)
	}

	inner := cmdLine + "\n\n" + strings.Join(styled, "\n")

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colSurf1).
		Background(colCrust).
		Padding(0, 2).
		Width(r.width - 4).
		Render(inner)
}

// ─── Workspace Card ───────────────────────────────────────────────────────────

// WorkspaceCard renders the workspace detection result at startup.
func (r *Renderer) WorkspaceCard(name, lang, framework, pkgMgr, gitBranch string, gitDirty bool, fileCount int) string {
	title := lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render("◎ " + name)

	rows := [][]string{}
	if framework != "" {
		rows = append(rows, []string{"Framework", framework})
	} else if lang != "" {
		rows = append(rows, []string{"Language", lang})
	}
	if pkgMgr != "" {
		rows = append(rows, []string{"Package Mgr", pkgMgr})
	}
	if gitBranch != "" {
		dirty := ""
		if gitDirty {
			dirty = " *"
		}
		rows = append(rows, []string{"Git", gitBranch + dirty})
	}
	if fileCount > 0 {
		rows = append(rows, []string{"Files", fmt.Sprintf("%d source files", fileCount)})
	}

	var sb strings.Builder
	sb.WriteString(title + "\n\n")
	for _, row := range rows {
		label := lipgloss.NewStyle().Foreground(colMuted).Width(12).Render(row[0])
		value := lipgloss.NewStyle().Foreground(colText).Render(row[1])
		sb.WriteString("  " + label + value + "\n")
	}

	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colBlue).
		Padding(1, 2).
		Render(sb.String())
}

// ─── Diff internals ───────────────────────────────────────────────────────────

type diffHunk struct {
	beforeLine int
	afterLine  int
	lines      []string
}

func makeDiffHunks(before, after string) []diffHunk {
	beforeLines := strings.Split(before, "\n")
	afterLines := strings.Split(after, "\n")

	// Simple line-by-line diff (LCS-free for now; use Myers diff for v0.2)
	var hunk diffHunk
	hunk.beforeLine = 1
	hunk.afterLine = 1

	bMax := len(beforeLines)
	aMax := len(afterLines)
	maxLen := bMax
	if aMax > maxLen {
		maxLen = aMax
	}

	for i := 0; i < maxLen; i++ {
		bLine := ""
		aLine := ""
		if i < bMax {
			bLine = beforeLines[i]
		}
		if i < aMax {
			aLine = afterLines[i]
		}
		if bLine == aLine {
			hunk.lines = append(hunk.lines, " "+bLine)
		} else {
			if bLine != "" {
				hunk.lines = append(hunk.lines, "-"+bLine)
			}
			if aLine != "" {
				hunk.lines = append(hunk.lines, "+"+aLine)
			}
		}
	}

	return []diffHunk{hunk}
}

func countDiffStats(hunks []diffHunk) (added, removed int) {
	for _, h := range hunks {
		for _, l := range h.lines {
			switch {
			case strings.HasPrefix(l, "+"):
				added++
			case strings.HasPrefix(l, "-"):
				removed++
			}
		}
	}
	return
}

func stringPtr(s string) *string {
	return &s
}

func boolPtr(b bool) *bool {
	return &b
}

func uintPtr(u uint) *uint {
	return &u
}

var CatppuccinTransparentStyle = ansi.StyleConfig{
	Document: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Color: stringPtr("#cdd6f4"),
		},
	},
	BlockQuote: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Color:  stringPtr("#a6adc8"),
			Italic: boolPtr(true),
		},
		Indent: uintPtr(2),
	},
	List: ansi.StyleList{
		LevelIndent: 2,
		StyleBlock: ansi.StyleBlock{
			StylePrimitive: ansi.StylePrimitive{
				Color: stringPtr("#cdd6f4"),
			},
		},
	},
	Heading: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Color: stringPtr("#cba6f7"),
			Bold:  boolPtr(true),
		},
	},
	H1: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Prefix: "# ",
			Color:  stringPtr("#cba6f7"),
			Bold:   boolPtr(true),
		},
	},
	H2: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Prefix: "## ",
			Color:  stringPtr("#89b4fa"),
			Bold:   boolPtr(true),
		},
	},
	H3: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Prefix: "### ",
			Color:  stringPtr("#89dceb"),
			Bold:   boolPtr(true),
		},
	},
	H4: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Prefix: "#### ",
			Color:  stringPtr("#a6e3a1"),
			Bold:   boolPtr(true),
		},
	},
	H5: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Prefix: "##### ",
			Color:  stringPtr("#f9e2af"),
			Bold:   boolPtr(true),
		},
	},
	H6: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Prefix: "###### ",
			Color:  stringPtr("#fab387"),
			Bold:   boolPtr(true),
		},
	},
	Strikethrough: ansi.StylePrimitive{
		CrossedOut: boolPtr(true),
	},
	Emph: ansi.StylePrimitive{
		Color:  stringPtr("#f9e2af"),
		Italic: boolPtr(true),
	},
	Strong: ansi.StylePrimitive{
		Bold:  boolPtr(true),
		Color: stringPtr("#fab387"),
	},
	HorizontalRule: ansi.StylePrimitive{
		Color:  stringPtr("#45475a"),
		Format: "\n────────\n",
	},
	Item: ansi.StylePrimitive{
		BlockPrefix: "• ",
		Color:       stringPtr("#cdd6f4"),
	},
	Enumeration: ansi.StylePrimitive{
		BlockPrefix: ". ",
		Color:       stringPtr("#89b4fa"),
	},
	Task: ansi.StyleTask{
		StylePrimitive: ansi.StylePrimitive{},
		Ticked:         "[✓] ",
		Unticked:       "[ ] ",
	},
	Link: ansi.StylePrimitive{
		Color:     stringPtr("#89b4fa"),
		Underline: boolPtr(true),
	},
	LinkText: ansi.StylePrimitive{
		Color: stringPtr("#cba6f7"),
	},
	Image: ansi.StylePrimitive{
		Color:     stringPtr("#89dceb"),
		Underline: boolPtr(true),
	},
	ImageText: ansi.StylePrimitive{
		Color:  stringPtr("#cba6f7"),
		Format: "Image: {{.text}} →",
	},
	Code: ansi.StyleBlock{
		StylePrimitive: ansi.StylePrimitive{
			Color: stringPtr("#f38ba8"),
		},
	},
	CodeBlock: ansi.StyleCodeBlock{
		StyleBlock: ansi.StyleBlock{
			StylePrimitive: ansi.StylePrimitive{
				Color: stringPtr("#cdd6f4"),
			},
		},
		Chroma: &ansi.Chroma{
			Text: ansi.StylePrimitive{
				Color: stringPtr("#cdd6f4"),
			},
			Error: ansi.StylePrimitive{
				Color: stringPtr("#f38ba8"),
			},
			Comment: ansi.StylePrimitive{
				Color: stringPtr("#6c7086"),
			},
			CommentPreproc: ansi.StylePrimitive{
				Color: stringPtr("#cba6f7"),
			},
			Keyword: ansi.StylePrimitive{
				Color: stringPtr("#cba6f7"),
			},
			KeywordReserved: ansi.StylePrimitive{
				Color: stringPtr("#cba6f7"),
			},
			KeywordNamespace: ansi.StylePrimitive{
				Color: stringPtr("#cba6f7"),
			},
			KeywordType: ansi.StylePrimitive{
				Color: stringPtr("#89b4fa"),
			},
			Operator: ansi.StylePrimitive{
				Color: stringPtr("#89dceb"),
			},
			Punctuation: ansi.StylePrimitive{
				Color: stringPtr("#cdd6f4"),
			},
			Name: ansi.StylePrimitive{
				Color: stringPtr("#89b4fa"),
			},
			NameBuiltin: ansi.StylePrimitive{
				Color: stringPtr("#89b4fa"),
			},
			NameTag: ansi.StylePrimitive{
				Color: stringPtr("#cba6f7"),
			},
			NameAttribute: ansi.StylePrimitive{
				Color: stringPtr("#a6e3a1"),
			},
			NameClass: ansi.StylePrimitive{
				Color: stringPtr("#89b4fa"),
			},
			NameConstant: ansi.StylePrimitive{
				Color: stringPtr("#fab387"),
			},
			NameDecorator: ansi.StylePrimitive{
				Color: stringPtr("#a6e3a1"),
			},
			NameFunction: ansi.StylePrimitive{
				Color: stringPtr("#89b4fa"),
			},
			LiteralNumber: ansi.StylePrimitive{
				Color: stringPtr("#fab387"),
			},
			LiteralString: ansi.StylePrimitive{
				Color: stringPtr("#a6e3a1"),
			},
			LiteralStringEscape: ansi.StylePrimitive{
				Color: stringPtr("#cba6f7"),
			},
			GenericDeleted: ansi.StylePrimitive{
				Color: stringPtr("#f38ba8"),
			},
			GenericEmph: ansi.StylePrimitive{
				Color:  stringPtr("#f9e2af"),
				Italic: boolPtr(true),
			},
			GenericInserted: ansi.StylePrimitive{
				Color: stringPtr("#a6e3a1"),
			},
			GenericStrong: ansi.StylePrimitive{
				Color: stringPtr("#fab387"),
				Bold:  boolPtr(true),
			},
			GenericSubheading: ansi.StylePrimitive{
				Color: stringPtr("#cba6f7"),
			},
		},
	},
	Table: ansi.StyleTable{
		StyleBlock: ansi.StyleBlock{
			StylePrimitive: ansi.StylePrimitive{},
		},
	},
	DefinitionDescription: ansi.StylePrimitive{
		BlockPrefix: "\n› ",
	},
}

// ─── Glamour init ─────────────────────────────────────────────────────────────

func newGlamour(width int) *glamour.TermRenderer {
	r, err := glamour.NewTermRenderer(
		glamour.WithStyles(CatppuccinTransparentStyle),
		glamour.WithWordWrap(width-6),
	)
	if err != nil {
		return nil
	}
	return r
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

func langLabel(ext string) string {
	m := map[string]string{
		"go":         "Go",
		"ts":         "TypeScript",
		"tsx":        "TSX",
		"js":         "JavaScript",
		"jsx":        "JSX",
		"py":         "Python",
		"rs":         "Rust",
		"java":       "Java",
		"kt":         "Kotlin",
		"sh":         "Shell",
		"bash":       "Bash",
		"json":       "JSON",
		"yaml":       "YAML",
		"yml":        "YAML",
		"toml":       "TOML",
		"md":         "Markdown",
		"html":       "HTML",
		"css":        "CSS",
		"sql":        "SQL",
		"dockerfile": "Dockerfile",
		"c":          "C",
		"cpp":        "C++",
		"h":          "C Header",
	}
	if label, ok := m[strings.ToLower(ext)]; ok {
		return label
	}
	if ext == "" {
		return "Plain Text"
	}
	return ext
}

func lineNumbers(code string) string {
	lines := strings.Split(code, "\n")
	var nums []string
	for i := range lines {
		nums = append(nums, fmt.Sprintf("%3d", i+1))
	}
	return strings.Join(nums, "\n")
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
