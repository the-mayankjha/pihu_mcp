package ui

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

// MCPTab is the active section in the MCP registry.
type MCPTab int

const (
	MCPTabDefault MCPTab = iota
	MCPTabInstalled
	MCPTabCatalog
	MCPTabDetails
	MCPTabHelp
)

type MCPTool struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

// CommunityMCPItem is normalized from the live PIHU Market API/catalog.
type CommunityMCPItem struct {
	ID          string
	DisplayName string
	Description string
	Author      string
	Version     string
	Category    string
	Runtime     string
	Transport   string
	Repository  string
	InstallCmd  string
	Prereqs     []string
	Tags        []string
	Tools       []MCPTool
	ToolCount   int
	Status      string
	Installed   bool
	IsDefault   bool
	Enabled     bool
	InstallPath string
	UpdatedAt   string
}

type rawMCPConfig struct {
	Servers map[string]struct {
		Command string            `json:"command"`
		Args    []string          `json:"args"`
		Env     map[string]string `json:"env"`
	} `json:"servers"`
}

type packageInventory struct {
	Packages map[string]map[string]any `json:"packages"`
	Servers  map[string]map[string]any `json:"servers"`
}

const (
	mcpIcoLoaded = "●"
	mcpIcoAvail  = "○"
	mcpIcoMark   = "◈"
	mcpIcoArrow  = "▸"
	mcpIcoDot    = "·"
	mcpIcoHelp   = "?"
	marketAPI    = "https://pihu.nfks.co.in/api/v2"
	officialMCPs = "https://raw.githubusercontent.com/the-mayankjha/pihu_mcp/pihu_market/market/catalog.json"
)

func mcpAPIBase() string {
	if configured := strings.TrimRight(strings.TrimSpace(os.Getenv("PIHU_MARKET_API_URL")), "/"); configured != "" {
		return configured
	}
	return marketAPI
}

func requestJSON(address string) (map[string]any, error) {
	client := &http.Client{Timeout: 5 * time.Second}
	request, err := http.NewRequest(http.MethodGet, address, nil)
	if err != nil {
		return nil, err
	}
	request.Header.Set("Accept", "application/json")
	request.Header.Set("User-Agent", "PIHU-CLI-MCP-Registry/1.0")
	response, err := client.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("registry returned %s", response.Status)
	}
	data, err := io.ReadAll(io.LimitReader(response.Body, 5<<20))
	if err != nil {
		return nil, err
	}
	var decoded map[string]any
	if err := json.Unmarshal(data, &decoded); err != nil {
		return nil, err
	}
	return decoded, nil
}

func asMap(value any) map[string]any {
	result, _ := value.(map[string]any)
	return result
}

func stringValue(value any) string {
	if text, ok := value.(string); ok {
		return strings.TrimSpace(text)
	}
	return ""
}

func nestedString(value any, key string) string {
	if text := stringValue(value); text != "" {
		return text
	}
	return stringValue(asMap(value)[key])
}

func stringList(value any) []string {
	items, _ := value.([]any)
	result := make([]string, 0, len(items))
	for _, item := range items {
		if text := stringValue(item); text != "" {
			result = append(result, text)
		}
	}
	return result
}

func parseTools(value any) []MCPTool {
	items, _ := value.([]any)
	tools := make([]MCPTool, 0, len(items))
	for _, item := range items {
		if name := stringValue(item); name != "" {
			tools = append(tools, MCPTool{Name: name})
			continue
		}
		entry := asMap(item)
		name := stringValue(entry["name"])
		if name != "" {
			tools = append(tools, MCPTool{Name: name, Description: stringValue(entry["description"])})
		}
	}
	return tools
}

func normalizeMCP(raw map[string]any) CommunityMCPItem {
	author := nestedString(raw["author"], "name")
	if author == "" {
		author = "Unknown author"
	}
	repository := nestedString(raw["repository"], "url")
	if repository == "" {
		repository = stringValue(raw["repository_url"])
	}
	runtime := nestedString(raw["runtime"], "type")
	transport := nestedString(raw["transport"], "type")
	tools := parseTools(raw["tools"])
	if len(tools) == 0 {
		tools = parseTools(raw["tools_provided"])
	}
	toolCount := len(tools)
	if value, ok := raw["tool_count"].(float64); ok && int(value) > toolCount {
		toolCount = int(value)
	}
	if value, ok := raw["tools_count"].(float64); ok && int(value) > toolCount {
		toolCount = int(value)
	}
	install := asMap(raw["installation"])
	installCmd := stringValue(raw["installCmd"])
	if installCmd == "" {
		installCmd = stringValue(raw["install_cmd"])
	}
	if installCmd == "" {
		installCmd = "pihu mcp install " + stringValue(raw["id"])
	}
	displayName := stringValue(raw["display_name"])
	if displayName == "" {
		displayName = stringValue(raw["displayName"])
	}
	if displayName == "" {
		displayName = stringValue(raw["name"])
	}
	if displayName == "" {
		displayName = stringValue(raw["id"])
	}
	prereqs := stringList(raw["requirements"])
	if len(prereqs) == 0 {
		if prerequisite := stringValue(raw["prereqs"]); prerequisite != "" {
			prereqs = []string{prerequisite}
		}
		if env := stringList(raw["env_vars_required"]); len(env) > 0 {
			prereqs = append(prereqs, env...)
		}
		if required := stringList(asMap(raw["permissions"])["env_vars_required"]); len(required) > 0 {
			prereqs = append(prereqs, required...)
		}
	}
	if len(prereqs) == 0 {
		if method := stringValue(install["type"]); method != "" {
			prereqs = []string{strings.ToUpper(method) + " runtime"}
		}
	}
	return CommunityMCPItem{
		ID: stringValue(raw["id"]), DisplayName: displayName,
		Description: stringValue(raw["description"]), Author: author,
		Version: stringValue(raw["version"]), Category: stringValue(raw["category"]),
		Runtime: runtime, Transport: transport, Repository: repository,
		InstallCmd: installCmd, Prereqs: prereqs,
		Tags: stringList(raw["tags"]), Tools: tools, ToolCount: toolCount,
		Status: stringValue(raw["status"]),
	}
}

func packagesFrom(data map[string]any) []CommunityMCPItem {
	items, _ := data["packages"].([]any)
	if items == nil {
		items, _ = data["servers"].([]any)
	}
	if items == nil {
		items, _ = data["results"].([]any)
	}
	packages := make([]CommunityMCPItem, 0, len(items))
	seen := map[string]bool{}
	for _, item := range items {
		entry := normalizeMCP(asMap(item))
		if entry.ID == "" || seen[entry.ID] {
			continue
		}
		seen[entry.ID] = true
		packages = append(packages, entry)
	}
	sort.Slice(packages, func(i, j int) bool {
		return strings.ToLower(packages[i].DisplayName) < strings.ToLower(packages[j].DisplayName)
	})
	return packages
}

// FetchLiveMCPCatalog uses the Market API first and the official repository catalog
// only as an offline fallback. It never substitutes a sample/hard-coded catalog.
func FetchLiveMCPCatalog() ([]CommunityMCPItem, string) {
	base := mcpAPIBase()
	endpoint := base + "/catalog?type=mcp&limit=100"
	if data, err := requestJSON(endpoint); err == nil {
		if catalog := packagesFrom(data); len(catalog) > 0 {
			return catalog, ""
		}
	}
	if data, err := requestJSON(officialMCPs); err == nil {
		if catalog := packagesFrom(data); len(catalog) > 0 {
			return catalog, "Market API unavailable · showing the official repository catalog"
		}
	}
	return nil, "Could not reach the PIHU MCP registry. Check your connection and press R to retry."
}

func SearchLiveMCP(query string) ([]CommunityMCPItem, string) {
	catalog, message := FetchLiveMCPCatalog()
	query = strings.ToLower(strings.TrimSpace(query))
	if query == "" {
		return catalog, message
	}
	results := make([]CommunityMCPItem, 0, len(catalog))
	for _, item := range catalog {
		searchable := strings.ToLower(strings.Join([]string{item.ID, item.DisplayName, item.Description, item.Category, item.Author, strings.Join(item.Tags, " ")}, " "))
		if strings.Contains(searchable, query) {
			results = append(results, item)
		}
	}
	return results, message
}

func LiveMCPInfo(id string) (CommunityMCPItem, error) {
	catalog, message := FetchLiveMCPCatalog()
	for _, item := range catalog {
		if item.ID == id {
			return FetchMCPManifest(item), nil
		}
	}
	if message != "" {
		return CommunityMCPItem{}, fmt.Errorf("%s", message)
	}
	return CommunityMCPItem{}, fmt.Errorf("MCP package %q is not in the registry", id)
}

// FetchMCPManifest enriches a selected catalog item with the published tool and
// installation contract rather than guessed CLI metadata.
func FetchMCPManifest(item CommunityMCPItem) CommunityMCPItem {
	address := mcpAPIBase() + "/packages/" + url.PathEscape(item.ID) + "/manifest"
	if data, err := requestJSON(address); err == nil {
		if manifest := asMap(data["manifest"]); manifest != nil {
			data = manifest
		}
		if enriched := normalizeMCP(data); enriched.ID != "" {
			if enriched.DisplayName == "" {
				enriched.DisplayName = item.DisplayName
			}
			if enriched.Description == "" {
				enriched.Description = item.Description
			}
			if enriched.Author == "Unknown author" {
				enriched.Author = item.Author
			}
			if enriched.Category == "" {
				enriched.Category = item.Category
			}
			if enriched.Version == "" {
				enriched.Version = item.Version
			}
			if enriched.Repository == "" {
				enriched.Repository = item.Repository
			}
			if enriched.InstallCmd == "" {
				enriched.InstallCmd = item.InstallCmd
			}
			if len(enriched.Tools) == 0 {
				enriched.Tools = item.Tools
			}
			if len(enriched.Prereqs) == 0 {
				enriched.Prereqs = item.Prereqs
			}
			return enriched
		}
	}
	return item
}

func defaultConfigCandidates() []string {
	candidates := []string{
		"agent/pihu/mcp/default_config.json",
		"mcp/default_config.json",
		"mcp/config.json",
		"src-tauri/pihu_mcps/agent/pihu/mcp/default_config.json",
		"src-tauri/pihu_mcps/mcp/config.json",
	}
	if executable, err := os.Executable(); err == nil {
		for dir := filepath.Dir(executable); dir != filepath.Dir(dir); dir = filepath.Dir(dir) {
			candidates = append(candidates, filepath.Join(dir, "agent", "pihu", "mcp", "default_config.json"))
			candidates = append(candidates, filepath.Join(dir, "mcp", "config.json"))
		}
	}
	return candidates
}

func readServerConfig(paths []string) (map[string]map[string]any, string) {
	for _, path := range paths {
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var payload map[string]any
		if json.Unmarshal(data, &payload) != nil {
			continue
		}
		servers := asMap(payload["servers"])
		if len(servers) == 0 {
			continue
		}
		result := make(map[string]map[string]any, len(servers))
		for id, server := range servers {
			result[id] = asMap(server)
		}
		return result, path
	}
	return nil, ""
}

func GetDefaultMCPs(catalog []CommunityMCPItem) []CommunityMCPItem {
	config, _ := readServerConfig(defaultConfigCandidates())
	byID := make(map[string]CommunityMCPItem, len(catalog))
	for _, item := range catalog {
		byID[item.ID] = item
	}
	defaults := make([]CommunityMCPItem, 0, len(config))
	for id, serverConfig := range config {
		item, ok := byID[id]
		if !ok {
			name := stringValue(serverConfig["display_name"])
			if name == "" {
				name = strings.ReplaceAll(strings.TrimSuffix(id, "-mcp"), "-", " ")
			}
			item = CommunityMCPItem{ID: id, DisplayName: strings.Title(name), Description: "Bundled with PIHU CLI", Author: "PIHU", InstallCmd: "Included with PIHU"}
		}
		item.IsDefault = true
		item.Status = "Default · enabled"
		defaults = append(defaults, item)
	}
	sort.Slice(defaults, func(i, j int) bool { return defaults[i].ID < defaults[j].ID })
	return defaults
}

func GetInstalledMCPs(catalog []CommunityMCPItem) []CommunityMCPItem {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil
	}
	defaultConfig, _ := readServerConfig(defaultConfigCandidates())
	paths := []string{filepath.Join(home, ".pihu", "installed.json"), filepath.Join(home, ".pihu", "mcp", "installed.json")}
	byID := make(map[string]CommunityMCPItem, len(catalog))
	for _, item := range catalog {
		byID[item.ID] = item
	}
	installed := map[string]CommunityMCPItem{}
	for _, path := range paths {
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var inventory packageInventory
		if json.Unmarshal(data, &inventory) != nil {
			continue
		}
		for id, record := range inventory.Packages {
			if kind := stringValue(record["type"]); kind != "" && kind != "mcp" {
				continue
			}
			item, ok := byID[id]
			if !ok {
				item = normalizeMCP(record)
			}
			if item.ID == "" {
				item.ID = id
			}
			if item.DisplayName == "" {
				item.DisplayName = stringValue(record["display_name"])
			}
			if item.DisplayName == "" {
				item.DisplayName = stringValue(record["name"])
			}
			if item.DisplayName == "" {
				item.DisplayName = id
			}
			if item.Description == "" {
				item.Description = stringValue(record["description"])
			}
			if item.Author == "Unknown author" {
				item.Author = nestedString(record["author"], "name")
			}
			if item.Version == "" {
				item.Version = stringValue(record["version"])
			}
			if len(item.Tools) == 0 {
				item.Tools = parseTools(record["tools"])
			}
			if item.ToolCount == 0 {
				item.ToolCount = len(item.Tools)
			}
			item.Installed = true
			item.Enabled = enabledValue(record)
			item.Status = "Installed"
			item.InstallPath = stringValue(record["install_path"])
			item.UpdatedAt = stringValue(record["installed_at"])
			installed[id] = item
		}
		for id, record := range inventory.Servers {
			if _, exists := installed[id]; exists {
				continue
			}
			if kind := stringValue(record["type"]); kind != "" && kind != "mcp" {
				continue
			}
			item, ok := byID[id]
			if !ok {
				item = normalizeMCP(record)
			}
			if item.ID == "" {
				item.ID = id
			}
			if item.DisplayName == "" {
				item.DisplayName = stringValue(record["display_name"])
			}
			if item.DisplayName == "" {
				item.DisplayName = id
			}
			if item.Description == "" {
				item.Description = stringValue(record["description"])
			}
			if item.Version == "" {
				item.Version = stringValue(record["version"])
			}
			if len(item.Tools) == 0 {
				item.Tools = parseTools(record["tools"])
			}
			if item.ToolCount == 0 {
				item.ToolCount = len(item.Tools)
			}
			item.Installed, item.Status = true, "Installed"
			item.Enabled = enabledValue(record)
			item.InstallPath = stringValue(record["install_path"])
			item.UpdatedAt = stringValue(record["installed_at"])
			installed[id] = item
		}
	}
	// Bundled default servers are part of the installed runtime even though
	// they are not recorded as marketplace installs in installed.json.
	for id, serverConfig := range defaultConfig {
		item, ok := installed[id]
		if !ok {
			item, ok = byID[id]
		}
		if !ok {
			name := stringValue(serverConfig["display_name"])
			if name == "" {
				name = strings.Title(strings.ReplaceAll(strings.TrimSuffix(id, "-mcp"), "-", " "))
			}
			item = CommunityMCPItem{ID: id, DisplayName: name, Description: "Bundled with PIHU CLI", Author: "PIHU", InstallCmd: "Included with PIHU"}
		}
		item.IsDefault = true
		item.Installed = true
		item.Enabled = true
		item.Status = "Default · installed"
		installed[id] = item
	}
	result := make([]CommunityMCPItem, 0, len(installed))
	for _, item := range installed {
		result = append(result, item)
	}
	sort.Slice(result, func(i, j int) bool {
		return strings.ToLower(result[i].DisplayName) < strings.ToLower(result[j].DisplayName)
	})
	return result
}

func enabledValue(record map[string]any) bool {
	enabled, ok := record["enabled"].(bool)
	return !ok || enabled
}

func RenderMCPRegistryModal(activeTab MCPTab, defaults, installed, catalog []CommunityMCPItem, selected int, detail *CommunityMCPItem, message string, detailScroll, w, h int) string {
	modalW := min(max(50, int(float64(w)*0.90)), 118)
	modalW = min(modalW, max(36, w-2))
	modalH := min(max(16, int(float64(h)*0.82)), 44)
	modalH = min(modalH, max(10, h-2))
	innerW := max(36, modalW-4)
	innerH := max(10, modalH-6)
	var rows []string
	rows = append(rows, mcpHeader(innerW), mcpPadRow("", innerW), mcpTabs(activeTab, innerW), mcpRule(innerW))
	rows = append(rows, mcpPadRow(mcpMuted(fmt.Sprintf("  %d default  ·  %d installed  ·  %d in catalog", len(defaults), len(installed), len(catalog))), innerW))
	rows = append(rows, mcpPadRow("", innerW))
	if message != "" {
		rows = append(rows, mcpPadRow(lipgloss.NewStyle().Foreground(colYellow).Render("  "+message), innerW), mcpPadRow("", innerW))
	}
	switch activeTab {
	case MCPTabDefault:
		rows = append(rows, mcpPackageList("Default MCPs", defaults, selected, innerW, innerH-8)...)
	case MCPTabInstalled:
		rows = append(rows, mcpPackageList("Installed MCPs", installed, selected, innerW, innerH-8)...)
	case MCPTabCatalog:
		rows = append(rows, mcpPackageList("MCP Catalog", catalog, selected, innerW, innerH-8)...)
	case MCPTabDetails:
		detailRows := mcpDetailRows(detail, innerW)
		budget := max(2, innerH-len(rows)-2)
		maxScroll := max(0, len(detailRows)-budget)
		if detailScroll > maxScroll {
			detailScroll = maxScroll
		}
		end := min(len(detailRows), detailScroll+budget)
		rows = append(rows, detailRows[detailScroll:end]...)
	case MCPTabHelp:
		rows = append(rows, mcpHelpRows(innerW)...)
	}
	for len(rows) < innerH-2 {
		rows = append(rows, mcpPadRow("", innerW))
	}
	if len(rows) > innerH-2 {
		rows = rows[:innerH-2]
	}
	rows = append(rows, mcpRule(innerW), mcpPadRow(lipgloss.NewStyle().Foreground(colMuted).Italic(true).Render("developed by Mayank Kumar Jha"), innerW))
	frame := lipgloss.NewStyle().Width(innerW).Padding(1, 1).Border(lipgloss.RoundedBorder()).BorderForeground(colMauve)
	if !TransparentBackground {
		frame = frame.Background(colBase)
	}
	return frame.Render(strings.Join(rows, "\n"))
}

func mcpHeader(width int) string {
	brand := lipgloss.NewStyle().Bold(true).Foreground(colCrust).Background(colPeach).Padding(0, 1).Render("PIHU MCPS")
	subtitle := lipgloss.NewStyle().Foreground(colSubtext).Bold(true).Render("  ·  MCP Registry")
	return mcpPadRow(brand+subtitle, width)
}

func mcpTabs(active MCPTab, width int) string {
	labels := []struct {
		tab        MCPTab
		label, key string
		color      lipgloss.Color
	}{
		{MCPTabDefault, "Default", "1", colGreen}, {MCPTabInstalled, "Installed", "2", colBlue},
		{MCPTabCatalog, "MCP Catalog", "3", colSky}, {MCPTabDetails, "Details", "D", colPeach}, {MCPTabHelp, "Help", "?", colYellow},
	}
	parts := make([]string, 0, len(labels))
	for _, label := range labels {
		text := fmt.Sprintf("%s [ %s ]", label.label, label.key)
		if active == label.tab {
			parts = append(parts, lipgloss.NewStyle().Bold(true).Foreground(colCrust).Background(label.color).Padding(0, 1).Render(text))
		} else {
			parts = append(parts, lipgloss.NewStyle().Foreground(colText).Render(text))
		}
	}
	return mcpPadRow(strings.Join(parts, "   "), width)
}

func mcpPackageList(title string, items []CommunityMCPItem, selected, width, budget int) []string {
	rows := []string{mcpPadRow(mcpSection(mcpIcoLoaded, title, len(items)), width), mcpPadRow("", width)}
	if len(items) == 0 {
		return append(rows, mcpPadRow(mcpMuted("  No MCPs in this section."), width))
	}
	if selected < 0 || selected >= len(items) {
		selected = 0
	}
	maxItems := max(1, budget-5)
	start := max(0, selected-maxItems/2)
	if start+maxItems > len(items) {
		start = max(0, len(items)-maxItems)
	}
	end := min(len(items), start+maxItems)
	for index := start; index < end; index++ {
		item := items[index]
		mark := mcpIcoAvail
		color := colText
		if item.IsDefault || item.Installed {
			mark = lipgloss.NewStyle().Foreground(colGreen).Render(mcpIcoLoaded)
		}
		if index == selected {
			color = colGreen
		}
		name := lipgloss.NewStyle().Foreground(color).Bold(index == selected).Render(mark + "  " + item.DisplayName)
		meta := fmt.Sprintf("%s  %s  %s  %d tools", item.Version, item.Category, item.Runtime, item.ToolCount)
		rows = append(rows, mcpPadRow("  "+name+"  "+mcpMuted(meta), width))
		if index == selected {
			rows = append(rows, mcpPadRow("     "+mcpMuted(mcpFit(item.Description, width-8)), width))
			rows = append(rows, mcpPadRow("     "+lipgloss.NewStyle().Foreground(colSubtext).Render(item.Author+"  ·  "+item.Transport), width))
			if len(item.Tools) > 0 {
				toolNames := make([]string, 0, min(5, len(item.Tools)))
				for _, tool := range item.Tools[:min(5, len(item.Tools))] {
					toolNames = append(toolNames, tool.Name)
				}
				rows = append(rows, mcpPadRow("     "+lipgloss.NewStyle().Foreground(colTeal).Render(strings.Join(toolNames, "  ·  ")), width))
			}
		}
	}
	return rows
}

func mcpDetailRows(item *CommunityMCPItem, width int) []string {
	if item == nil {
		return []string{mcpPadRow(mcpMuted("Select an MCP from Default, Installed, or Catalog and press Enter."), width)}
	}
	rows := []string{mcpPadRow(lipgloss.NewStyle().Foreground(colText).Bold(true).Render("  "+item.DisplayName), width)}
	rows = append(rows, mcpPadRow("  "+mcpMuted(item.Description), width), mcpPadRow("", width))
	rows = append(rows, mcpDetailField("Author", item.Author, width), mcpDetailField("Version", item.Version, width), mcpDetailField("Category", item.Category, width), mcpDetailField("Runtime", item.Runtime+" · "+item.Transport, width))
	if item.Repository != "" {
		rows = append(rows, mcpDetailField("Repository", item.Repository, width))
	}
	if len(item.Tags) > 0 {
		rows = append(rows, mcpDetailField("Tags", strings.Join(item.Tags, " · "), width))
	}
	if len(item.Prereqs) > 0 {
		rows = append(rows, mcpDetailField("Requirements", strings.Join(item.Prereqs, " · "), width))
	}
	rows = append(rows, mcpPadRow("", width), mcpPadRow(lipgloss.NewStyle().Foreground(colYellow).Bold(true).Render("  Install"), width), mcpPadRow("  "+lipgloss.NewStyle().Foreground(colGreen).Render(item.InstallCmd), width))
	if item.InstallPath != "" {
		rows = append(rows, mcpDetailField("Installed at", item.InstallPath, width))
	}
	toolCount := item.ToolCount
	if toolCount == 0 {
		toolCount = len(item.Tools)
	}
	rows = append(rows, mcpPadRow("", width), mcpPadRow(lipgloss.NewStyle().Foreground(colMuted).Bold(true).Render(fmt.Sprintf("  Tools (%d)", toolCount)), width))
	for _, tool := range item.Tools {
		line := lipgloss.NewStyle().Foreground(colTeal).Render("  ◇ " + tool.Name)
		if tool.Description != "" {
			line += "  " + mcpMuted(tool.Description)
		}
		rows = append(rows, mcpPadRow("  "+mcpFit(line, width-2), width))
	}
	return rows
}

func mcpDetailField(label, value string, width int) string {
	return mcpPadRow("  "+lipgloss.NewStyle().Foreground(colMuted).Width(15).Render(label)+lipgloss.NewStyle().Foreground(colSubtext).Render(mcpFit(value, width-19)), width)
}

func mcpHelpRows(width int) []string {
	return []string{
		mcpPadRow(mcpSection(mcpIcoHelp, "Keyboard", 8), width), mcpPadRow("", width),
		mcpPadRow("  1 / 2 / 3   Default, Installed, Catalog", width),
		mcpPadRow("  Enter       Open details for selected MCP", width),
		mcpPadRow("  D           Show details for selected MCP", width),
		mcpPadRow("  I           Open install information", width),
		mcpPadRow("  R           Refresh live registry and inventory", width),
		mcpPadRow("  ↑ / ↓       Select MCP", width), mcpPadRow("  Esc         Close registry", width),
	}
}

func mcpSection(icon, label string, count int) string {
	return lipgloss.NewStyle().Foreground(colMuted).Bold(true).Render(fmt.Sprintf("%s  %s (%d)", icon, label, count))
}
func mcpMuted(text string) string { return lipgloss.NewStyle().Foreground(colMuted).Render(text) }
func mcpRule(width int) string {
	return lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", max(1, width)))
}
func mcpPadRow(text string, width int) string {
	return lipgloss.NewStyle().Width(width).MaxWidth(width).Render(text)
}
func mcpFit(text string, width int) string {
	if width < 4 || lipgloss.Width(text) <= width {
		return text
	}
	runes := []rune(text)
	keep := max(1, width-3)
	if keep > len(runes) {
		keep = len(runes)
	}
	return string(runes[:keep]) + "..."
}
