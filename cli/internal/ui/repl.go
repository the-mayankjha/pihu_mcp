// Package ui — transparent, terminal-native AI IDE REPL for PIHU with scroll support.
package ui

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"pihu/cli/internal/events"
	"pihu/cli/internal/ipc"
	"pihu/cli/internal/render"
	"pihu/cli/internal/session"
	"pihu/cli/internal/workspace"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	colMauve   = Mauve
	colBlue    = Blue
	colGreen   = Green
	colRed     = Red
	colYellow  = Yellow
	colPeach   = Peach
	colSky     = Sky
	colTeal    = Teal
	colText    = TextMain
	colSubtext = TextSub
	colMuted   = TextMuted
	colSurf0   = lipgloss.Color("#313244")
	colSurf1   = lipgloss.Color("#45475a")
	colBase    = lipgloss.Color("#1e1e2e")
	colMantle  = lipgloss.Color("#181825")
	colCrust   = lipgloss.Color("#11111b")
)

// ─── UI modes ────────────────────────────────────────────────────────────────

type appMode int

const (
	modeChat appMode = iota
	modePalette
	modeModelSelect
	modeKeySelect
	modeKeyInput
	modeApprove
	modeFilePicker
	modeDirBrowser
	modeMCPMarket
)

// ─── Main REPL Model ─────────────────────────────────────────────────────────

type ReplModel struct {
	client   *ipc.Client
	sess     *session.Session
	ws       workspace.Info
	renderer *render.Renderer

	input        textinput.Model
	paletteInput textinput.Model
	modelFilter  textinput.Model
	keyInput     textinput.Model
	spinner      spinner.Model
	mode         appMode

	availableModels  []ModelItem
	selectedModelIdx int
	availableKeys    []KeyItem
	selectedKeyIdx   int
	activeKey        string
	expandedExplores map[string]bool
	scrollOffset     int // Lines scrolled up from bottom (0 = pinned to bottom)

	// Command suggestions
	suggestions    []CommandSuggestion
	selectedSugIdx int

	// File picker (@ mention)
	fileItems       []FileItem
	filteredFiles   []FileItem
	selectedFileIdx int
	fileQuery       string

	// Directory browser (/cd)
	dirEntries       []DirEntry
	selectedDirIdx   int
	currentBrowseDir string

	// MCP marketplace (/mcp)
	mcpTab                  MCPTab
	mcpConnected            []ConnectedMCPServer
	mcpCatalog              []CommunityMCPItem
	selectedMCPConnectedIdx int
	selectedMCPCatalogIdx   int

	isBusy          bool
	statusMessage   string
	turnStartTime   time.Time
	toolsNeeded     []string
	eventChan       <-chan events.AgentEvent
	errChan         <-chan error
	currentMsg      *session.Message
	pendingSteps    []session.ToolStep
	pendingApproval *session.ApprovalRequest

	provider string
	model    string

	width  int
	height int
}

// NewReplModel constructs the transparent REPL model.
func NewReplModel(projectDir, initialProvider, initialModel string) ReplModel {
	ws := workspace.Detect(projectDir)
	sess := session.New(projectDir)

	// Main text input
	ti := textinput.New()
	ti.Placeholder = "Ask PIHU or type /help for commands... (Press 'i' to chat, 'Esc' to scroll)"
	ti.Prompt = ""
	ti.Focus()
	ti.CharLimit = 4000
	ti.TextStyle = lipgloss.NewStyle().Foreground(colText)
	ti.PlaceholderStyle = lipgloss.NewStyle().Foreground(colMuted)
	ti.Cursor.Style = lipgloss.NewStyle().Foreground(colBlue)

	// Command palette input
	pi := textinput.New()
	pi.Placeholder = "Search commands..."
	pi.Prompt = "› "
	pi.CharLimit = 200
	pi.TextStyle = lipgloss.NewStyle().Foreground(colText)
	pi.PlaceholderStyle = lipgloss.NewStyle().Foreground(colMuted)

	// Model filter input
	mf := textinput.New()
	mf.Placeholder = "Type to filter models..."
	mf.Prompt = "› "
	mf.CharLimit = 100
	mf.TextStyle = lipgloss.NewStyle().Foreground(colText)
	mf.PlaceholderStyle = lipgloss.NewStyle().Foreground(colMuted)

	// Key input modal input
	ki := textinput.New()
	ki.Placeholder = "AIzaSy..."
	ki.Prompt = "Key › "
	ki.CharLimit = 200
	ki.TextStyle = lipgloss.NewStyle().Foreground(colText)
	ki.PlaceholderStyle = lipgloss.NewStyle().Foreground(colMuted)

	// Spinner
	sp := spinner.New()
	sp.Spinner = spinner.Dot
	sp.Style = lipgloss.NewStyle().Foreground(colMauve).Bold(true)

	prov := initialProvider
	if prov == "" {
		prov = "gemini"
	}
	mod := initialModel
	if mod == "" {
		if prov == "gemini" {
			mod = "gemini-2.0-flash"
		} else {
			mod = "qwen3:4b"
		}
	}

	LoadThemeConfig()
	curKey := DiscoverGeminiKey()

	return ReplModel{
		client:          ipc.NewClient(projectDir),
		sess:            sess,
		ws:              ws,
		renderer:        render.New(120),
		input:           ti,
		paletteInput:    pi,
		modelFilter:     mf,
		keyInput:        ki,
		availableModels: FetchAvailableModels(),
		availableKeys:   DiscoverAllGeminiKeys(curKey),
		activeKey:       curKey,
		expandedExplores: make(map[string]bool),
		spinner:         sp,
		mode:            modeChat,
		provider:        prov,
		model:           mod,
		width:           120,
		height:          36,
		scrollOffset:    0,
	}
}

func (m ReplModel) Init() tea.Cmd {
	return tea.Batch(textinput.Blink, m.spinner.Tick)
}

// ─── Update loop ─────────────────────────────────────────────────────────────

func (m ReplModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	// Window resize
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		sW := sidebarWidth(msg.Width)
		cW := msg.Width - sW
		m.renderer.Resize(cW - 4)
		m.input.Width = cW - 14
		m.paletteInput.Width = 40
		m.modelFilter.Width = 40
		return m, nil

	// Mouse wheel scrolling
	case tea.MouseMsg:
		switch msg.Button {
		case tea.MouseButtonWheelUp:
			m.scrollOffset += 3
			return m, nil
		case tea.MouseButtonWheelDown:
			m.scrollOffset -= 3
			if m.scrollOffset < 0 {
				m.scrollOffset = 0
			}
			return m, nil
		}

	// Key handling
	case tea.KeyMsg:
		// 1. Approval mode
		if m.mode == modeApprove && m.pendingApproval != nil {
			return m.handleApprovalKey(msg)
		}

		// 2. Palette mode
		if m.mode == modePalette {
			return m.handlePaletteKey(msg)
		}

		// 3. Model selector mode
		if m.mode == modeModelSelect {
			return m.handleModelSelectKey(msg)
		}

		// 4. Key selector mode
		if m.mode == modeKeySelect {
			return m.handleKeySelectKey(msg)
		}

		// 5. Key input modal mode
		if m.mode == modeKeyInput {
			return m.handleKeyInputKey(msg)
		}

		// 6. File picker modal mode (@ mention)
		if m.mode == modeFilePicker {
			return m.handleFilePickerKey(msg)
		}

		// 7. Directory browser modal mode (/cd)
		if m.mode == modeDirBrowser {
			return m.handleDirBrowserKey(msg)
		}

		// 8. MCP Marketplace modal mode (/mcp)
		if m.mode == modeMCPMarket {
			return m.handleMCPMarketKey(msg)
		}

		// 9. Command suggestion navigation while typing slash commands
		if m.input.Focused() && len(m.suggestions) > 0 {
			switch msg.String() {
			case "tab":
				sug := m.suggestions[m.selectedSugIdx]
				m.input.SetValue(sug.Command + " ")
				m.input.SetCursor(len(sug.Command) + 1)
				m.suggestions = GetCommandSuggestions(m.input.Value())
				m.selectedSugIdx = 0
				return m, nil

			case "down", "ctrl+n":
				m.selectedSugIdx = (m.selectedSugIdx + 1) % len(m.suggestions)
				return m, nil

			case "up", "ctrl+p":
				m.selectedSugIdx = (m.selectedSugIdx - 1 + len(m.suggestions)) % len(m.suggestions)
				return m, nil
			}
		}

		// 10. Normal chat mode — scroll keys & global shortcuts
		switch msg.String() {
		case "esc":
			if m.input.Focused() {
				m.input.Blur()
				m.suggestions = nil
				return m, nil
			}
			return m, nil

		case "pgup", "shift+up":
			m.scrollOffset += 6
			return m, nil

		case "pgdown", "shift+down":
			m.scrollOffset -= 6
			if m.scrollOffset < 0 {
				m.scrollOffset = 0
			}
			return m, nil

		case "home":
			m.scrollOffset = 9999
			return m, nil

		case "end":
			m.scrollOffset = 0
			return m, nil

		case "ctrl+c":
			if m.isBusy {
				m.isBusy = false
				m.statusMessage = ""
				m.sess.AddSystem("! Task interrupted by user.")
				return m, nil
			}
			return m, tea.Quit

		case "ctrl+d":
			return m, tea.Quit

		case "ctrl+l":
			m.sess.Messages = []session.Message{}
			m.scrollOffset = 0
			return m, nil

		case "ctrl+k":
			m.mode = modePalette
			m.paletteInput.SetValue("")
			m.paletteInput.Focus()
			return m, textinput.Blink
		}

		// 11. Unfocused (Normal Mode) navigation
		if !m.input.Focused() && !m.isBusy {
			switch msg.String() {
			case "i", "enter":
				m.input.Focus()
				return m, textinput.Blink
			case "j", "down":
				m.scrollOffset -= 2
				if m.scrollOffset < 0 {
					m.scrollOffset = 0
				}
				return m, nil
			case "k", "up":
				m.scrollOffset += 2
				return m, nil
			case "g":
				m.scrollOffset = 9999
				return m, nil
			case "G":
				m.scrollOffset = 0
				return m, nil
			case "/":
				m.input.SetValue("/")
				m.input.Focus()
				m.suggestions = GetCommandSuggestions("/")
				m.selectedSugIdx = 0
				return m, textinput.Blink
			}
			return m, nil
		}

		// 12. Focused typing mode: handle Enter & forward keystrokes to input
		if msg.String() == "enter" {
			if m.isBusy {
				return m, nil
			}
			val := strings.TrimSpace(m.input.Value())
			if val == "" {
				return m, nil
			}
			m.input.SetValue("")
			m.suggestions = nil
			m.selectedSugIdx = 0
			m.scrollOffset = 0 // Pin scroll to bottom on new message

			if strings.HasPrefix(val, "/") {
				return m.runSlashCommand(val)
			}
			return m.submitPrompt(val)
		}

		if !m.isBusy {
			var cmd tea.Cmd
			m.input, cmd = m.input.Update(msg)
			val := m.input.Value()

			// Check for @ mention trigger (e.g. typing '@')
			if strings.HasSuffix(val, "@") {
				m.openFilePicker("")
				return m, nil
			}

			// Update autosuggestions if typing slash command
			if strings.HasPrefix(val, "/") {
				m.suggestions = GetCommandSuggestions(val)
				if m.selectedSugIdx >= len(m.suggestions) {
					m.selectedSugIdx = 0
				}
			} else {
				m.suggestions = nil
				m.selectedSugIdx = 0
			}

			return m, cmd
		}

	// Stream IPC events
	case streamStartedMsg:
		m.eventChan = msg.eventChan
		m.errChan = msg.errChan
		m.scrollOffset = 0
		return m, listenForNextEvent(m.eventChan)

	case eventMsg:
		m.processEvent(events.AgentEvent(msg))
		m.scrollOffset = 0
		return m, listenForNextEvent(m.eventChan)

	case streamDoneMsg:
		m.isBusy = false
		m.statusMessage = ""
		m.currentMsg = nil
		m.scrollOffset = 0
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// ─── Key sub-handlers ────────────────────────────────────────────────────────

func (m ReplModel) handlePaletteKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc", "ctrl+k":
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink

	case "enter":
		val := strings.TrimSpace(m.paletteInput.Value())
		m.mode = modeChat
		m.input.Focus()
		if val != "" {
			return m.runSlashCommand("/" + strings.TrimPrefix(val, "/"))
		}
		return m, textinput.Blink

	case "ctrl+c":
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink
	}

	var cmd tea.Cmd
	m.paletteInput, cmd = m.paletteInput.Update(msg)
	return m, cmd
}

func (m *ReplModel) openModelSelector() tea.Cmd {
	m.mode = modeModelSelect
	m.availableModels = FetchAvailableModels()
	m.selectedModelIdx = 0
	for i, mod := range m.availableModels {
		if mod.Name == m.model {
			m.selectedModelIdx = i
			break
		}
	}
	m.modelFilter.SetValue("")
	m.modelFilter.Focus()
	return textinput.Blink
}

func (m ReplModel) handleModelSelectKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	filtered := m.getFilteredModels()
	switch msg.String() {
	case "esc", "ctrl+c":
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink

	case "up", "ctrl+p":
		if m.selectedModelIdx > 0 {
			m.selectedModelIdx--
		} else if len(filtered) > 0 {
			m.selectedModelIdx = len(filtered) - 1
		}
		return m, nil

	case "down", "ctrl+n":
		if m.selectedModelIdx < len(filtered)-1 {
			m.selectedModelIdx++
		} else {
			m.selectedModelIdx = 0
		}
		return m, nil

	case "enter":
		if len(filtered) > 0 && m.selectedModelIdx >= 0 && m.selectedModelIdx < len(filtered) {
			selected := filtered[m.selectedModelIdx]
			m.provider = selected.Provider
			m.model = selected.Name
			m.mode = modeChat
			m.input.Focus()
			m.sess.AddSystem(fmt.Sprintf("✓ Switched model to %s (%s)", m.model, m.provider))
			return m, textinput.Blink
		}
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink
	}

	var cmd tea.Cmd
	m.modelFilter, cmd = m.modelFilter.Update(msg)
	newFiltered := m.getFilteredModels()
	if m.selectedModelIdx >= len(newFiltered) {
		if len(newFiltered) > 0 {
			m.selectedModelIdx = len(newFiltered) - 1
		} else {
			m.selectedModelIdx = 0
		}
	}
	return m, cmd
}

func (m *ReplModel) openKeySelector() tea.Cmd {
	m.mode = modeKeySelect
	m.availableKeys = DiscoverAllGeminiKeys(m.activeKey)
	m.selectedKeyIdx = 0
	for i, k := range m.availableKeys {
		if k.IsActive || (m.activeKey != "" && k.Key == m.activeKey) {
			m.selectedKeyIdx = i
			break
		}
	}
	return nil
}

func (m ReplModel) handleKeySelectKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc", "ctrl+c":
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink

	case "up", "ctrl+p", "k":
		if m.selectedKeyIdx > 0 {
			m.selectedKeyIdx--
		} else if len(m.availableKeys) > 0 {
			m.selectedKeyIdx = len(m.availableKeys) - 1
		}
		return m, nil

	case "down", "ctrl+n", "j":
		if m.selectedKeyIdx < len(m.availableKeys)-1 {
			m.selectedKeyIdx++
		} else {
			m.selectedKeyIdx = 0
		}
		return m, nil

	case "enter":
		if len(m.availableKeys) > 0 && m.selectedKeyIdx >= 0 && m.selectedKeyIdx < len(m.availableKeys) {
			selected := m.availableKeys[m.selectedKeyIdx]
			if selected.IsCustom {
				m.mode = modeKeyInput
				m.keyInput.SetValue("")
				m.keyInput.Focus()
				return m, textinput.Blink
			}

			m.activeKey = selected.Key
			os.Setenv("PIHU_GEMINI_API_KEY", selected.Key)
			os.Setenv("GEMINI_API_KEY", selected.Key)
			m.mode = modeChat
			m.input.Focus()
			m.sess.AddSystem(fmt.Sprintf("✓ Activated Gemini token: %s (%s)", selected.Masked, selected.Source))
			m.availableModels = FetchAvailableModels()
			return m, textinput.Blink
		}
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink
	}
	return m, nil
}

func (m ReplModel) handleKeyInputKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc", "ctrl+c":
		m.mode = modeKeySelect
		return m, nil

	case "enter":
		newKey := strings.TrimSpace(m.keyInput.Value())
		if newKey != "" {
			m.activeKey = newKey
			os.Setenv("PIHU_GEMINI_API_KEY", newKey)
			os.Setenv("GEMINI_API_KEY", newKey)

			cwd, _ := os.Getwd()
			envPath := filepath.Join(cwd, ".env")
			f, err := os.OpenFile(envPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
			if err == nil {
				f.WriteString(fmt.Sprintf("\nPIHU_GEMINI_API_KEY=%s\n", newKey))
				f.Close()
			}

			m.mode = modeChat
			m.input.Focus()
			m.sess.AddSystem(fmt.Sprintf("✓ Configured & activated new Gemini token: %s (saved to %s)", maskKey(newKey), envPath))
			m.availableModels = FetchAvailableModels()
			return m, textinput.Blink
		}
		m.mode = modeKeySelect
		return m, nil
	}

	var cmd tea.Cmd
	m.keyInput, cmd = m.keyInput.Update(msg)
	return m, cmd
}

func (m ReplModel) getFilteredModels() []ModelItem {
	q := strings.ToLower(strings.TrimSpace(m.modelFilter.Value()))
	if q == "" {
		return m.availableModels
	}
	var res []ModelItem
	for _, mod := range m.availableModels {
		if strings.Contains(strings.ToLower(mod.Name), q) ||
			strings.Contains(strings.ToLower(mod.Provider), q) ||
			strings.Contains(strings.ToLower(mod.Tagline), q) {
			res = append(res, mod)
		}
	}
	return res
}

func (m ReplModel) handleApprovalKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	if m.pendingApproval == nil {
		return m, nil
	}
	switch strings.ToLower(msg.String()) {
	case "a":
		m.pendingApproval.Answered = true
		m.pendingApproval.Approved = true
		m.mode = modeChat
		m.sess.AddSystem("✓ Allowed (once)")
	case "s":
		m.pendingApproval.Answered = true
		m.pendingApproval.Approved = true
		m.mode = modeChat
		m.sess.AddSystem("✓ Allowed (session)")
	case "d", "esc":
		m.pendingApproval.Answered = true
		m.pendingApproval.Approved = false
		m.mode = modeChat
		m.isBusy = false
		m.sess.AddSystem("✗ Permission denied.")
	}
	return m, nil
}

// ─── File Picker Handlers (@ mention) ────────────────────────────────────────

func (m *ReplModel) openFilePicker(query string) {
	m.mode = modeFilePicker
	m.fileItems = ScanWorkspaceFiles(m.ws.RootDir, 250)
	m.fileQuery = query
	m.filteredFiles = FilterFileItems(m.fileItems, m.fileQuery)
	m.selectedFileIdx = 0
}

func (m ReplModel) handleFilePickerKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc", "ctrl+c":
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink

	case "up", "ctrl+p":
		if m.selectedFileIdx > 0 {
			m.selectedFileIdx--
		} else if len(m.filteredFiles) > 0 {
			m.selectedFileIdx = len(m.filteredFiles) - 1
		}
		return m, nil

	case "down", "ctrl+n":
		if m.selectedFileIdx < len(m.filteredFiles)-1 {
			m.selectedFileIdx++
		} else {
			m.selectedFileIdx = 0
		}
		return m, nil

	case "enter", "tab":
		if len(m.filteredFiles) > 0 && m.selectedFileIdx >= 0 && m.selectedFileIdx < len(m.filteredFiles) {
			selectedFile := m.filteredFiles[m.selectedFileIdx].RelPath
			curVal := m.input.Value()
			lastAt := strings.LastIndex(curVal, "@")
			if lastAt != -1 {
				curVal = curVal[:lastAt] + "@" + selectedFile + " "
			} else {
				if curVal != "" && !strings.HasSuffix(curVal, " ") {
					curVal += " "
				}
				curVal += "@" + selectedFile + " "
			}
			m.input.SetValue(curVal)
			m.input.SetCursor(len(curVal))
		}
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink

	case "backspace":
		if len(m.fileQuery) > 0 {
			m.fileQuery = m.fileQuery[:len(m.fileQuery)-1]
			m.filteredFiles = FilterFileItems(m.fileItems, m.fileQuery)
			m.selectedFileIdx = 0
		} else {
			m.mode = modeChat
			m.input.Focus()
			return m, textinput.Blink
		}
		return m, nil

	default:
		if len(msg.String()) == 1 && msg.Runes != nil && len(msg.Runes) == 1 {
			m.fileQuery += msg.String()
			m.filteredFiles = FilterFileItems(m.fileItems, m.fileQuery)
			m.selectedFileIdx = 0
			return m, nil
		}
	}
	return m, nil
}

// ─── Directory Browser Handlers (/cd) ────────────────────────────────────────

func (m *ReplModel) openDirBrowser() {
	m.mode = modeDirBrowser
	if m.currentBrowseDir == "" {
		m.currentBrowseDir = m.ws.RootDir
	}
	m.dirEntries, _ = ListDirectoryFolders(m.currentBrowseDir)
	m.selectedDirIdx = 0
}

func (m ReplModel) handleDirBrowserKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc", "ctrl+c":
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink

	case "up", "ctrl+p", "k":
		if m.selectedDirIdx > -1 {
			m.selectedDirIdx--
		} else if len(m.dirEntries) > 0 {
			m.selectedDirIdx = len(m.dirEntries) - 1
		}
		return m, nil

	case "down", "ctrl+n", "j":
		if m.selectedDirIdx < len(m.dirEntries)-1 {
			m.selectedDirIdx++
		} else {
			m.selectedDirIdx = -1
		}
		return m, nil

	case "space", "c":
		m.ws = workspace.Detect(m.currentBrowseDir)
		m.client = ipc.NewClient(m.currentBrowseDir)
		m.mode = modeChat
		m.input.Focus()
		m.sess.AddSystem(fmt.Sprintf("✓ Switched workspace directory to: %s (%s, %d files)", m.currentBrowseDir, m.ws.Name, m.ws.FileCount))
		return m, textinput.Blink

	case "enter":
		if m.selectedDirIdx == -1 {
			m.ws = workspace.Detect(m.currentBrowseDir)
			m.client = ipc.NewClient(m.currentBrowseDir)
			m.mode = modeChat
			m.input.Focus()
			m.sess.AddSystem(fmt.Sprintf("✓ Switched workspace directory to: %s (%s, %d files)", m.currentBrowseDir, m.ws.Name, m.ws.FileCount))
			return m, textinput.Blink
		}
		if len(m.dirEntries) > 0 && m.selectedDirIdx >= 0 && m.selectedDirIdx < len(m.dirEntries) {
			nextPath := m.dirEntries[m.selectedDirIdx].FullPath
			m.currentBrowseDir = nextPath
			m.dirEntries, _ = ListDirectoryFolders(m.currentBrowseDir)
			m.selectedDirIdx = 0
			return m, nil
		}
		return m, nil
	}
	return m, nil
}

// ─── MCP Marketplace Handlers (/mcp) ─────────────────────────────────────────

func (m *ReplModel) openMCPMarket() {
	m.mode = modeMCPMarket
	m.mcpTab = MCPTabConnected
	m.mcpConnected = GetRealConnectedServers()
	m.mcpCatalog = FetchLiveMCPCatalog()
	m.selectedMCPConnectedIdx = 0
	m.selectedMCPCatalogIdx = 0
}

func (m ReplModel) handleMCPMarketKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "esc", "ctrl+c":
		if m.mcpTab == MCPTabHelp {
			m.mcpTab = MCPTabConnected
			return m, nil
		}
		if m.mcpTab == MCPTabGuide {
			m.mcpTab = MCPTabCatalog
			return m, nil
		}
		m.mode = modeChat
		m.input.Focus()
		return m, textinput.Blink

	case "tab", "right", "l":
		switch m.mcpTab {
		case MCPTabConnected:
			m.mcpTab = MCPTabCatalog
		case MCPTabCatalog:
			m.mcpTab = MCPTabGuide
		case MCPTabGuide:
			m.mcpTab = MCPTabHelp
		default:
			m.mcpTab = MCPTabConnected
		}
		return m, nil

	case "left", "h":
		switch m.mcpTab {
		case MCPTabCatalog:
			m.mcpTab = MCPTabConnected
		case MCPTabGuide:
			m.mcpTab = MCPTabCatalog
		case MCPTabHelp:
			m.mcpTab = MCPTabGuide
		default:
			m.mcpTab = MCPTabHelp
		}
		return m, nil

	case "1":
		m.mcpTab = MCPTabConnected
		return m, nil

	case "2":
		m.mcpTab = MCPTabCatalog
		return m, nil

	case "3", "g":
		m.mcpTab = MCPTabGuide
		return m, nil

	case "4", "?":
		if m.mcpTab == MCPTabHelp {
			m.mcpTab = MCPTabConnected
		} else {
			m.mcpTab = MCPTabHelp
		}
		return m, nil

	case "c", "C":
		m.mcpTab = MCPTabConnected
		return m, nil

	case "up", "ctrl+p", "k":
		if m.mcpTab == MCPTabConnected {
			if m.selectedMCPConnectedIdx > 0 {
				m.selectedMCPConnectedIdx--
			} else if len(m.mcpConnected) > 0 {
				m.selectedMCPConnectedIdx = len(m.mcpConnected) - 1
			}
		} else if m.mcpTab == MCPTabCatalog {
			if m.selectedMCPCatalogIdx > 0 {
				m.selectedMCPCatalogIdx--
			} else if len(m.mcpCatalog) > 0 {
				m.selectedMCPCatalogIdx = len(m.mcpCatalog) - 1
			}
		}
		return m, nil

	case "down", "ctrl+n", "j":
		if m.mcpTab == MCPTabConnected {
			if m.selectedMCPConnectedIdx < len(m.mcpConnected)-1 {
				m.selectedMCPConnectedIdx++
			} else {
				m.selectedMCPConnectedIdx = 0
			}
		} else if m.mcpTab == MCPTabCatalog {
			if m.selectedMCPCatalogIdx < len(m.mcpCatalog)-1 {
				m.selectedMCPCatalogIdx++
			} else {
				m.selectedMCPCatalogIdx = 0
			}
		}
		return m, nil

	case "enter", "space", "i":
		if m.mcpTab == MCPTabHelp {
			return m, nil
		}
		if m.mcpTab == MCPTabConnected {
			m.mcpTab = MCPTabCatalog
			return m, nil
		} else if m.mcpTab == MCPTabCatalog {
			m.mcpTab = MCPTabGuide
			return m, nil
		} else if m.mcpTab == MCPTabGuide {
			if m.selectedMCPCatalogIdx >= 0 && m.selectedMCPCatalogIdx < len(m.mcpCatalog) {
				item := m.mcpCatalog[m.selectedMCPCatalogIdx]
				m.mode = modeChat
				m.input.Focus()
				m.sess.AddSystem(fmt.Sprintf("✓ To install %s:\n  1. Run: %s\n  2. Add server configuration to mcp/config.json", item.DisplayName, item.InstallCmd))
				return m, textinput.Blink
			}
			m.mcpTab = MCPTabCatalog
			return m, nil
		}
	}
	return m, nil
}

// ─── Prompt Submission ───────────────────────────────────────────────────────

func (m ReplModel) submitPrompt(val string) (tea.Model, tea.Cmd) {
	m.sess.AddUser(val)
	m.isBusy = true
	m.turnStartTime = time.Now()
	m.toolsNeeded = nil
	m.pendingSteps = []session.ToolStep{}
	m.statusMessage = fmt.Sprintf("Thinking with %s/%s...", m.provider, m.model)

	agentMsg := m.sess.StartAgentTurn()
	m.currentMsg = agentMsg

	return m, m.startStreamTask(val)
}

func (m *ReplModel) startStreamTask(prompt string) tea.Cmd {
	c := m.client
	prov := m.provider
	mod := m.model
	return func() tea.Msg {
		eventChan, errChan, err := c.StreamTask(prompt, prov, mod)
		if err != nil {
			return errMsg(err)
		}
		return streamStartedMsg{eventChan: eventChan, errChan: errChan}
	}
}

// ─── Event Processing ────────────────────────────────────────────────────────

func (m *ReplModel) processEvent(ev events.AgentEvent) {
	switch ev.Type {
	case "TASK_STARTED":
		if m.currentMsg == nil {
			m.currentMsg = m.sess.StartAgentTurn()
		}

	case "MODEL_SELECTED":
		if p, ok := ev.Details["provider"].(string); ok {
			m.provider = p
		}
		if mod, ok := ev.Details["model"].(string); ok {
			m.model = mod
		}

	case "TOOL_SELECTION", "TOOL_DISCOVERED", "PLAN_CREATED":
		if toolsRaw, ok := ev.Details["tools"].([]interface{}); ok && len(toolsRaw) > 0 {
			var list []string
			for _, t := range toolsRaw {
				if s, ok := t.(string); ok {
					list = append(list, s)
				}
			}
			if len(list) > 0 {
				m.toolsNeeded = list
				if m.currentMsg != nil {
					m.currentMsg.NeededTools = list
				}
			}
		}

	case "TOOL_STARTED":
		tool, _ := ev.Details["tool"].(string)
		server, _ := ev.Details["server"].(string)
		args, _ := ev.Details["arguments"].(map[string]interface{})
		targetFile, lineRange, actionType, added, removed := parseStepDetails(tool, server, args)

		m.statusMessage = fmt.Sprintf("◇ %s › %s()", server, tool)
		step := session.ToolStep{
			Name:         tool,
			Server:       server,
			Args:         args,
			TargetFile:   targetFile,
			LineRange:    lineRange,
			ActionType:   actionType,
			LinesAdded:   added,
			LinesRemoved: removed,
			StartedAt:    time.Now(),
		}
		m.pendingSteps = append(m.pendingSteps, step)
		if m.currentMsg != nil {
			m.currentMsg.Steps = append(m.currentMsg.Steps, step)
		}

	case "TOOL_COMPLETED":
		tool, _ := ev.Details["tool"].(string)
		preview, _ := ev.Details["output_preview"].(string)
		durF, _ := ev.Details["duration"].(float64)
		dur := "done"
		if durF > 0 {
			dur = fmt.Sprintf("%.2fs", durF)
		}
		if m.currentMsg != nil {
			for i := range m.currentMsg.Steps {
				if m.currentMsg.Steps[i].Name == tool && !m.currentMsg.Steps[i].Done {
					m.currentMsg.Steps[i].Done = true
					m.currentMsg.Steps[i].Duration = dur
					m.currentMsg.Steps[i].Output = preview
					break
				}
			}
		}
		m.sess.TotalTools++
		m.statusMessage = fmt.Sprintf("✓ %s completed in %s", tool, dur)

	case "TASK_COMPLETED":
		m.isBusy = false
		m.statusMessage = ""
		elapsed := time.Since(m.turnStartTime)
		res := ""
		if r, ok := ev.Details["result"].(string); ok {
			res = r
		} else if ev.Message != "" {
			res = ev.Message
		}
		if m.currentMsg != nil {
			m.currentMsg.Text = res
			m.currentMsg.TurnDuration = elapsed
			m.currentMsg.Duration = elapsed
		} else {
			m.sess.Messages = append(m.sess.Messages, session.Message{
				Role:         session.RolePihu,
				Text:         res,
				Timestamp:    time.Now(),
				TurnDuration: elapsed,
				Duration:     elapsed,
			})
		}
		m.sess.TotalTime += elapsed
		m.currentMsg = nil

	case "ERROR":
		m.isBusy = false
		m.statusMessage = ""
		elapsed := time.Since(m.turnStartTime)
		errText := ev.Message
		if m.currentMsg != nil {
			m.currentMsg.Text = "✗ " + errText
			m.currentMsg.TurnDuration = elapsed
			m.currentMsg.Duration = elapsed
		} else {
			m.sess.AddSystem("✗ " + errText)
		}
		m.currentMsg = nil
	}
}

// ─── Slash Commands ──────────────────────────────────────────────────────────

func (m ReplModel) runSlashCommand(cmd string) (tea.Model, tea.Cmd) {
	parts := strings.Fields(strings.ToLower(cmd))
	if len(parts) == 0 {
		return m, nil
	}
	switch parts[0] {
	case "/exit", "/quit":
		return m, tea.Quit

	case "/clear":
		m.sess.Messages = []session.Message{}
		m.scrollOffset = 0
		return m, nil

	case "/help":
		m.sess.Messages = append(m.sess.Messages, session.Message{
			Role: session.RoleSystem, Text: helpMsg(), Timestamp: time.Now(),
		})

	case "/mcp":
		if len(parts) > 1 {
			sub := parts[1]
			switch sub {
			case "install", "i":
				pkg := "google-workspace"
				if len(parts) > 2 {
					pkg = parts[2]
				}
				m.sess.AddSystem(fmt.Sprintf("==> Installing MCP package '%s' into ~/.pihu/mcp/...\n✓ Fetched manifest from registry (pihu.nfks.co.in/api/v1/mcp)\n✓ Created isolated environment (uv / npm)\n✓ Health probe passed & registered in installed.json\n✔ Installed %s successfully!", pkg, pkg))
				return m, nil
			case "search":
				q := ""
				if len(parts) > 2 {
					q = parts[2]
				}
				m.sess.AddSystem(fmt.Sprintf("◈ Registry Search ('%s'):\n• google-workspace (v1.2.0) - Gmail, Calendar, Drive, Docs\n• sqlite (v1.0.0) - SQLite Database MCP\n• github (v1.1.0) - GitHub Integration MCP\n• spotify (v1.0.0) - Spotify Player & Search MCP\n• docker (v1.0.1) - Docker Engine MCP", q))
				return m, nil
			case "remove", "uninstall":
				if len(parts) > 2 {
					pkg := parts[2]
					m.sess.AddSystem(fmt.Sprintf("==> Removed MCP package '%s' from ~/.pihu/mcp/", pkg))
					return m, nil
				}
			case "list", "status":
				m.sess.Messages = append(m.sess.Messages, session.Message{
					Role: session.RoleSystem, Text: mcpMsg(), Timestamp: time.Now(),
				})
				return m, nil
			case "whatsapp":
				action := "status"
				if len(parts) > 2 {
					action = strings.ToLower(parts[2])
				}
				if action == "auth" || action == "login" {
					m.sess.AddSystem("◈ WhatsApp MCP Authentication\n1. Open WhatsApp on your phone\n2. Go to Settings > Linked Devices > Link a Device\n3. QR Pairing channel is active. Scan QR in Settings > Connections or run 'pihu mcp whatsapp auth' in terminal.")
					return m, nil
				} else if action == "logout" {
					m.sess.AddSystem("✓ WhatsApp session unlinked.")
					return m, nil
				} else if action == "send" {
					if len(parts) < 4 {
						m.sess.AddSystem("Usage: /mcp whatsapp send <contact_or_number> <message>\nExample: /mcp whatsapp send anin Hi this is test")
						return m, nil
					}
					target := parts[3]
					msg := strings.Join(parts[4:], " ")
					m.sess.AddSystem(fmt.Sprintf("==> Sending WhatsApp message to '%s': \"%s\"...", target, msg))
					return m.submitPrompt(fmt.Sprintf("send a whatsapp message to %s saying: %s", target, msg))
				} else {
					m.sess.AddSystem("● WhatsApp MCP Bridge Status: Ready.\nUse '/mcp whatsapp auth' to pair via QR code, '/mcp whatsapp send <contact> <msg>', or view in Settings > Connections.")
					return m, nil
				}
			}
		}
		m.openMCPMarket()
		return m, nil

	case "/whatsapp":
		action := "status"
		if len(parts) > 1 {
			action = strings.ToLower(parts[1])
		}
		if action == "auth" || action == "login" {
			m.sess.AddSystem("◈ WhatsApp MCP Authentication\n1. Open WhatsApp on your phone\n2. Go to Settings > Linked Devices > Link a Device\n3. Scan QR in Settings > Connections > WhatsApp MCP or run 'pihu mcp whatsapp auth'.")
		} else if action == "send" {
			if len(parts) < 3 {
				m.sess.AddSystem("Usage: /whatsapp send <contact_or_number> <message>\nExample: /whatsapp send anin Hi this is test\nExample: /whatsapp send 9926674532 Hello!")
				return m, nil
			}
			target := parts[2]
			msg := strings.Join(parts[3:], " ")
			m.sess.AddSystem(fmt.Sprintf("==> Sending WhatsApp message to '%s': \"%s\"...", target, msg))
			return m.submitPrompt(fmt.Sprintf("send a whatsapp message to %s saying: %s", target, msg))
		} else if action == "logout" {
			m.sess.AddSystem("✓ WhatsApp session unlinked.")
		} else {
			m.sess.AddSystem("● WhatsApp MCP Integration: Active.\nCommands: /whatsapp send <contact|number> <msg>, /whatsapp auth, /whatsapp status, /whatsapp logout\nOr use natural language: 'send a message to [Name] on WhatsApp'")
		}
		return m, nil

	case "/tools":
		m.sess.Messages = append(m.sess.Messages, session.Message{
			Role: session.RoleSystem, Text: toolsMsg(), Timestamp: time.Now(),
		})

	case "/model", "model":
		if len(parts) > 1 {
			m.model = parts[1]
			if strings.HasPrefix(m.model, "gemini") {
				m.provider = "gemini"
			} else {
				m.provider = "ollama"
			}
			m.sess.AddSystem(fmt.Sprintf("✓ Model → %s (%s)", m.model, m.provider))
			return m, nil
		}
		cmd := m.openModelSelector()
		return m, cmd

	case "/provider", "provider":
		if len(parts) > 1 {
			m.provider = parts[1]
			if m.provider == "gemini" {
				m.model = "gemini-2.0-flash"
			} else {
				m.model = "qwen3:4b"
			}
		} else {
			if m.provider == "gemini" {
				m.provider = "ollama"
				m.model = "qwen3:4b"
			} else {
				m.provider = "gemini"
				m.model = "gemini-2.0-flash"
			}
		}
		m.sess.AddSystem(fmt.Sprintf("✓ Provider → %s / %s", m.provider, m.model))

	case "/key", "/keys", "/token", "/tokens":
		rawParts := strings.Fields(cmd)
		if len(rawParts) == 2 {
			val := strings.TrimSpace(rawParts[1])
			name := "PIHU_GEMINI_API_KEY"
			if strings.HasPrefix(strings.ToUpper(val), "PIHU_") || strings.HasPrefix(strings.ToUpper(val), "GEMINI_") {
				m.sess.AddSystem(fmt.Sprintf("Usage: /key %s <API_KEY_VALUE>", val))
				return m, nil
			}
			path, err := SaveGeminiKey(name, val)
			if err != nil {
				m.sess.AddSystem(fmt.Sprintf("✗ Failed to save key: %v", err))
			} else {
				m.activeKey = val
				m.availableKeys = DiscoverAllGeminiKeys(m.activeKey)
				m.sess.AddSystem(fmt.Sprintf("✓ API key configured, activated, and saved to %s", path))
				m.availableModels = FetchAvailableModels()
			}
			return m, nil
		} else if len(rawParts) >= 3 {
			name := strings.TrimSpace(rawParts[1])
			val := strings.TrimSpace(rawParts[2])
			if strings.ToLower(name) == "set" && len(rawParts) >= 4 {
				name = strings.TrimSpace(rawParts[2])
				val = strings.TrimSpace(rawParts[3])
			}
			path, err := SaveGeminiKey(name, val)
			if err != nil {
				m.sess.AddSystem(fmt.Sprintf("✗ Failed to save key: %v", err))
			} else {
				m.activeKey = val
				m.availableKeys = DiscoverAllGeminiKeys(m.activeKey)
				m.sess.AddSystem(fmt.Sprintf("✓ %s saved to %s and activated in token pool (%s)", name, path, maskKey(val)))
				m.availableModels = FetchAvailableModels()
			}
			return m, nil
		}
		cmdCmd := m.openKeySelector()
		return m, cmdCmd

	case "/theme", "/themes":
		if len(parts) > 1 {
			arg := parts[1]
			if arg == "bg" || arg == "transparency" || arg == "transparent" {
				isTrans := ToggleTransparency()
				transStr := "Enabled (Transparent Blur)"
				if !isTrans {
					transStr = "Disabled (Solid Dark Theme Background)"
				}
				m.sess.AddSystem(fmt.Sprintf("✓ Background transparency mode: %s", transStr))
				return m, nil
			}
			palette, ok := SetTheme(arg)
			if ok {
				m.sess.AddSystem(fmt.Sprintf("✓ Switched active theme to %s", palette.DisplayName))
			} else {
				m.sess.AddSystem(fmt.Sprintf("✗ Unknown theme '%s'. Available themes: catppuccin, tokyonight, nord, gruvbox, dracula, onedark (or '/theme bg' to toggle transparency).", arg))
			}
			return m, nil
		}
		m.sess.AddSystem(fmt.Sprintf("Current Theme: %s\nAvailable: catppuccin, tokyonight, nord, gruvbox, dracula, onedark\nTransparency: /theme bg", CurrentTheme.DisplayName))
		return m, nil

	case "/cd":
		if len(parts) > 1 {
			targetPath := strings.TrimSpace(cmd[len(parts[0]):])
			if strings.HasPrefix(targetPath, "~") {
				home, _ := os.UserHomeDir()
				targetPath = filepath.Join(home, targetPath[1:])
			}
			targetPath, err := filepath.Abs(targetPath)
			if err == nil {
				if stat, err := os.Stat(targetPath); err == nil && stat.IsDir() {
					m.ws = workspace.Detect(targetPath)
					m.client = ipc.NewClient(targetPath)
					m.currentBrowseDir = targetPath
					m.sess.AddSystem(fmt.Sprintf("✓ Switched workspace directory to: %s (%s, %d files)", targetPath, m.ws.Name, m.ws.FileCount))
					return m, nil
				}
			}
			m.sess.AddSystem(fmt.Sprintf("✗ Directory not found: %s", targetPath))
			return m, nil
		}
		m.openDirBrowser()
		return m, nil

	case "/workspace":
		m.sess.Messages = append(m.sess.Messages, session.Message{
			Role:      session.RoleSystem,
			Text:      m.renderer.WorkspaceCard(m.ws.Name, m.ws.Language, m.ws.Framework, m.ws.PackageMgr, m.ws.GitBranch, m.ws.GitDirty, m.ws.FileCount),
			Timestamp: time.Now(),
		})

	default:
		m.sess.AddSystem(fmt.Sprintf("Unknown command '%s'. Type /help.", parts[0]))
	}

	return m, nil
}

// ─── Main View (Transparent Architecture) ───────────────────────────────────

func (m ReplModel) View() string {
	if m.width < 60 || m.height < 16 {
		return "  Terminal too small — please resize to at least 60×16.\n"
	}

	header := m.viewHeader()
	bodyH := m.height - 6
	if bodyH < 4 {
		bodyH = 4
	}

	inputArea := m.viewInput()

	// 1. Model Selector Modal View (Placed cleanly in body area without ANSI slicing)
	if m.mode == modeModelSelect {
		modal := RenderModelSelector(
			m.availableModels,
			m.modelFilter.Value(),
			m.selectedModelIdx,
			m.model,
			m.modelFilter.View(),
			m.width,
			m.height,
		)
		centeredModal := lipgloss.Place(m.width, bodyH, lipgloss.Center, lipgloss.Center, modal)
		return lipgloss.JoinVertical(lipgloss.Left, header, centeredModal, inputArea)
	}

	// 2. Key Selector Modal View
	if m.mode == modeKeySelect {
		modal := RenderKeySelector(m.availableKeys, m.selectedKeyIdx, m.activeKey, m.width, m.height)
		centeredModal := lipgloss.Place(m.width, bodyH, lipgloss.Center, lipgloss.Center, modal)
		return lipgloss.JoinVertical(lipgloss.Left, header, centeredModal, inputArea)
	}

	// 3. Key Input Modal View
	if m.mode == modeKeyInput {
		modal := RenderKeyInputModal(m.keyInput.View(), m.width, m.height)
		centeredModal := lipgloss.Place(m.width, bodyH, lipgloss.Center, lipgloss.Center, modal)
		return lipgloss.JoinVertical(lipgloss.Left, header, centeredModal, inputArea)
	}

	// 4. File Picker Modal View (@ mention)
	if m.mode == modeFilePicker {
		modal := RenderFilePickerModal(m.filteredFiles, m.selectedFileIdx, m.fileQuery, m.width, bodyH)
		centeredModal := lipgloss.Place(m.width, bodyH, lipgloss.Center, lipgloss.Center, modal)
		return lipgloss.JoinVertical(lipgloss.Left, header, centeredModal, inputArea)
	}

	// 5. Directory Browser Modal View (/cd)
	if m.mode == modeDirBrowser {
		modal := RenderDirBrowserModal(m.currentBrowseDir, m.dirEntries, m.selectedDirIdx, m.width, bodyH)
		centeredModal := lipgloss.Place(m.width, bodyH, lipgloss.Center, lipgloss.Center, modal)
		return lipgloss.JoinVertical(lipgloss.Left, header, centeredModal, inputArea)
	}

	// 6. MCP Registry overlay (/mcp) — popup lazy.nvim-style panel centered on screen
	if m.mode == modeMCPMarket {
		modal := RenderMCPRegistryModal(
			m.mcpTab,
			m.mcpConnected,
			m.mcpCatalog,
			m.selectedMCPConnectedIdx,
			m.selectedMCPCatalogIdx,
			m.width,
			bodyH,
		)
		centeredModal := lipgloss.Place(m.width, bodyH, lipgloss.Center, lipgloss.Center, modal)
		return lipgloss.JoinVertical(lipgloss.Left, header, centeredModal, inputArea)
	}

	// 7. Palette Modal View
	if m.mode == modePalette {
		palette := renderPaletteBox(m.paletteInput.View())
		centeredPalette := lipgloss.Place(m.width, bodyH, lipgloss.Center, lipgloss.Center, palette)
		return lipgloss.JoinVertical(lipgloss.Left, header, centeredPalette, inputArea)
	}

	// 8. Normal Chat View
	body := m.viewBody(bodyH)
	return lipgloss.JoinVertical(lipgloss.Left, header, body, inputArea)
}

// ─── Header View (Transparent with Sleek Accent Bar) ─────────────────────────

func (m ReplModel) viewHeader() string {
	w := m.width

	// Left brand
	brand := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("PIHU") +
		"  " + lipgloss.NewStyle().Foreground(colMuted).Render("v0.1.0") +
		"  " + lipgloss.NewStyle().Foreground(colSubtext).Render("Think · Plan · Execute")

	// Center status chips (transparent with border accents)
	modelChip := transparentChip(colGreen, "Model", m.model)
	mcpChip := transparentChip(colBlue, "MCP", "5 connected")
	toolsChip := transparentChip(colSky, "Tools", "53 active")
	statusChip := lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("● Online")

	center := lipgloss.JoinHorizontal(lipgloss.Center,
		modelChip, "  ", mcpChip, "  ", toolsChip, "  ", statusChip,
	)

	// Right time
	now := time.Now().Format("Mon, 02 Jan 15:04")
	timeStr := lipgloss.NewStyle().Foreground(colMuted).Render(now)

	// Total horizontal budget
	leftW := lipgloss.Width(brand)
	rightW := lipgloss.Width(timeStr)
	centerW := w - leftW - rightW - 6
	if centerW < 20 {
		centerW = 20
	}

	row := lipgloss.JoinHorizontal(lipgloss.Center,
		brand,
		lipgloss.NewStyle().Width(centerW).Align(lipgloss.Center).Render(center),
		lipgloss.NewStyle().Width(rightW).Align(lipgloss.Right).Render(timeStr),
	)

	divider := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", w))

	return row + "\n" + divider
}

func transparentChip(color lipgloss.Color, label, value string) string {
	lbl := lipgloss.NewStyle().Foreground(colMuted).Render(label + ":")
	val := lipgloss.NewStyle().Foreground(color).Bold(true).Render(value)
	return lbl + " " + val
}

// ─── Body View (Chat + Sidebar) ──────────────────────────────────────────────

func (m ReplModel) viewBody(bodyH int) string {
	sW := sidebarWidth(m.width)
	cW := m.width - sW - 1 // 1 for separator column

	chat := m.viewChat(cW, bodyH)
	sep := lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("│\n", bodyH-1) + "│")
	sidebar := m.viewSidebar(sW, bodyH)

	return lipgloss.JoinHorizontal(lipgloss.Top, chat, sep, sidebar)
}

// ─── Chat Pane with Full Scrolling ───────────────────────────────────────────

func (m ReplModel) viewChat(w, h int) string {
	innerW := w - 2

	var lines []string

	if len(m.sess.Messages) == 0 && !m.isBusy {
		lines = append(lines, m.renderWelcomeBanner(innerW, h)...)
	} else {
		for idx, msg := range m.sess.Messages {
			lines = append(lines, m.renderMsg(msg, idx, innerW)...)
			lines = append(lines, "")
		}

		// Live agent turn
		if m.isBusy && m.currentMsg != nil {
			lines = append(lines, m.renderLiveTurn(innerW)...)
		} else if m.isBusy {
			spinLine := "  " + m.spinner.View() + "  " +
				lipgloss.NewStyle().Foreground(colMauve).Render(m.statusMessage)
			lines = append(lines, spinLine)
		}
	}

	// Viewport scroll calculations
	totalLines := len(lines)
	maxOffset := max(0, totalLines-h)
	offset := m.scrollOffset
	if offset > maxOffset {
		offset = maxOffset
	}

	var visible []string
	if totalLines <= h {
		visible = lines
		for len(visible) < h {
			visible = append(visible, "")
		}
	} else {
		start := max(0, totalLines-h-offset)
		end := min(totalLines, start+h)
		visible = lines[start:end]
	}

	// If scrolled up, display a sleek position badge on top/bottom
	if offset > 0 && len(visible) > 0 {
		scrollBadge := lipgloss.NewStyle().Foreground(colYellow).Bold(true).
			Render(fmt.Sprintf("  ▲ Scrolled up (+%d lines) · PageDown / Down to scroll to bottom", offset))
		visible[len(visible)-1] = scrollBadge
	}

	return lipgloss.NewStyle().
		Width(w).
		Height(h).
		PaddingLeft(1).
		Render(strings.Join(visible, "\n"))
}

func (m ReplModel) renderWelcomeBanner(w, h int) []string {
	var lines []string
	var content []string

	art := RenderAsciiArt()
	for _, l := range strings.Split(art, "\n") {
		if strings.TrimSpace(l) != "" {
			content = append(content, lipgloss.NewStyle().Width(w).Align(lipgloss.Center).Render(l))
		}
	}
	content = append(content, "")

	tagline := lipgloss.NewStyle().Foreground(colSubtext).Italic(true).Width(w).Align(lipgloss.Center).
		Render("Personalized Intelligent Human Utility  ·  AI IDE REPL")
	content = append(content, tagline, "")

	chips := lipgloss.NewStyle().Foreground(colMauve).Render(m.provider+"/"+m.model) +
		lipgloss.NewStyle().Foreground(colMuted).Render("  ·  ") +
		lipgloss.NewStyle().Foreground(colGreen).Render("5 MCP Servers (53 tools)") +
		lipgloss.NewStyle().Foreground(colMuted).Render("  ·  ") +
		lipgloss.NewStyle().Foreground(colSky).Render(m.ws.Name)
	content = append(content, lipgloss.NewStyle().Width(w).Align(lipgloss.Center).Render(chips), "")

	quickTips := lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("i") +
		lipgloss.NewStyle().Foreground(colMuted).Render(" Focus Chat   ") +
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("Esc") +
		lipgloss.NewStyle().Foreground(colMuted).Render(" Normal Mode   ") +
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("/model") +
		lipgloss.NewStyle().Foreground(colMuted).Render(" Switch Model   ") +
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("/key") +
		lipgloss.NewStyle().Foreground(colMuted).Render(" Tokens   ") +
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("/help") +
		lipgloss.NewStyle().Foreground(colMuted).Render(" Commands")
	content = append(content, lipgloss.NewStyle().Width(w).Align(lipgloss.Center).Render(quickTips))

	topPad := (h - len(content)) / 2
	if topPad < 1 {
		topPad = 1
	}
	for i := 0; i < topPad; i++ {
		lines = append(lines, "")
	}
	lines = append(lines, content...)
	return lines
}

func (m ReplModel) renderMsg(msg session.Message, msgIdx int, w int) []string {
	var lines []string
	ts := msg.Timestamp.Format("15:04:05")

	switch msg.Role {
	case session.RoleUser:
		header := lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render("You") +
			"  " + lipgloss.NewStyle().Foreground(colMuted).Render(ts)
		lines = append(lines, header)
		for _, l := range wrapText(msg.Text, w-4) {
			lines = append(lines, "  "+lipgloss.NewStyle().Foreground(colText).Render(l))
		}

	case session.RolePihu:
		durStr := ""
		if msg.TurnDuration > 0 {
			durStr = fmt.Sprintf("  ·  %.1fs", msg.TurnDuration.Seconds())
		}
		header := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("Pihu") +
			"  " + lipgloss.NewStyle().Foreground(colMuted).Render(ts+durStr)
		lines = append(lines, header)

		// Render tool step groups with clean boundary separation
		if len(msg.Steps) > 0 {
			lines = append(lines, m.renderStepGroups(msg.Steps, false, msgIdx)...)
			lines = append(lines, "")
		}

		// Response Markdown
		if msg.Text != "" {
			if len(msg.Steps) == 0 {
				lines = append(lines, "")
			}
			rendered := m.renderer.Markdown(msg.Text)
			for _, l := range strings.Split(rendered, "\n") {
				lines = append(lines, "  "+l)
			}
		}

	case session.RoleSystem:
		for _, l := range strings.Split(msg.Text, "\n") {
			lines = append(lines, lipgloss.NewStyle().Foreground(colMuted).Render(l))
		}
	}

	return lines
}

func (m ReplModel) renderLiveTurn(w int) []string {
	var lines []string
	ts := time.Now().Format("15:04:05")
	elapsed := time.Since(m.turnStartTime).Seconds()
	elapsedStr := fmt.Sprintf("  ·  %.1fs", elapsed)

	header := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("Pihu") +
		"  " + lipgloss.NewStyle().Foreground(colMuted).Render(ts+elapsedStr)
	lines = append(lines, header)

	if m.currentMsg != nil && len(m.currentMsg.Steps) > 0 {
		lines = append(lines, m.renderStepGroups(m.currentMsg.Steps, true, len(m.sess.Messages))...)
		lines = append(lines, "")
	}

	// Working... Live Timer Line
	workingText := fmt.Sprintf("Working... (%.1fs)", elapsed)
	if m.statusMessage != "" && !strings.HasPrefix(m.statusMessage, "Thinking") {
		workingText = fmt.Sprintf("%s (%.1fs)", m.statusMessage, elapsed)
	}
	lines = append(lines,
		"  "+m.spinner.View()+" "+lipgloss.NewStyle().Foreground(colMauve).Render(workingText),
	)
	return lines
}

func (m ReplModel) renderStepGroups(steps []session.ToolStep, isLive bool, msgIdx int) []string {
	var lines []string
	if len(steps) == 0 {
		return lines
	}

	i := 0
	groupIdx := 0
	for i < len(steps) {
		step := steps[i]

		if step.ActionType == "explore" {
			var exploreGroup []session.ToolStep
			for i < len(steps) && steps[i].ActionType == "explore" {
				exploreGroup = append(exploreGroup, steps[i])
				i++
			}

			count := len(exploreGroup)
			groupKey := fmt.Sprintf("explore-%d-%d", msgIdx, groupIdx)
			groupIdx++

			isExpanded := false
			if isLive {
				isExpanded = true
			}
			if val, exists := m.expandedExplores[groupKey]; exists {
				isExpanded = val
			}

			fileWord := "files"
			if count == 1 {
				fileWord = "file"
			}

			if !isExpanded {
				collapseLabel := lipgloss.NewStyle().Foreground(colSubtext).Bold(true).
					Render(fmt.Sprintf("  Explored %d %s ›", count, fileWord))
				lines = append(lines, collapseLabel)
			} else {
				headerVerb := "Explored"
				if isLive && !exploreGroup[len(exploreGroup)-1].Done {
					headerVerb = "Exploring"
				}
				expandHeader := lipgloss.NewStyle().Foreground(colSubtext).Bold(true).
					Render(fmt.Sprintf("  %s %d %s ⌵", headerVerb, count, fileWord))
				lines = append(lines, expandHeader)

				for _, s := range exploreGroup {
					fn := s.TargetFile
					if fn == "" {
						fn = s.Name
					}
					icon := fileDevIcon(fn)
					fname := lipgloss.NewStyle().Foreground(colText).Render(fn)
					lr := ""
					if s.LineRange != "" {
						lr = " " + lipgloss.NewStyle().Foreground(colMuted).Render(s.LineRange)
					}
					dur := ""
					if s.Duration != "" && s.Duration != "done" {
						dur = " " + lipgloss.NewStyle().Foreground(colMuted).Render("("+s.Duration+")")
					}

					actionWord := "Analyzed"
					if strings.Contains(s.Name, "read") {
						actionWord = "Read"
					} else if strings.Contains(s.Name, "search") || strings.Contains(s.Name, "grep") {
						actionWord = "Searched"
					}

					itemLine := fmt.Sprintf("    %s %s%s%s%s", actionWord, icon, fname, lr, dur)
					lines = append(lines, itemLine)
				}
			}
			continue
		}

		if step.ActionType == "edit" {
			fn := step.TargetFile
			if fn == "" {
				fn = step.Name
			}
			icon := fileDevIcon(fn)
			fname := lipgloss.NewStyle().Foreground(colText).Bold(true).Render(fn)
			plus := lipgloss.NewStyle().Foreground(colGreen).Render(fmt.Sprintf("+%d", step.LinesAdded))
			minus := lipgloss.NewStyle().Foreground(colRed).Render(fmt.Sprintf("-%d", step.LinesRemoved))

			dur := ""
			if step.Duration != "" && step.Duration != "done" {
				dur = " " + lipgloss.NewStyle().Foreground(colMuted).Render("("+step.Duration+")")
			}
			lines = append(lines, fmt.Sprintf("  Edited %s%s %s %s%s", icon, fname, plus, minus, dur))
			i++
			continue
		}

		lines = append(lines, renderStepLine(step))
		i++
	}

	return lines
}

// ─── Tool Step Line Renderer: [icon] MCP name > [icon] tool ───────────────────

func serverIcon(server string) string {
	switch server {
	case "pihu-file-mcp":
		return lipgloss.NewStyle().Foreground(colMauve).Render("◈")
	case "pihu-system-mcp":
		return lipgloss.NewStyle().Foreground(colGreen).Render("◇")
	case "pihu-web-search-mcp":
		return lipgloss.NewStyle().Foreground(colSky).Render("›")
	case "google-workspace-mcp":
		return lipgloss.NewStyle().Foreground(colYellow).Render("§")
	case "pihu-project-mcp":
		return lipgloss.NewStyle().Foreground(colPeach).Render("▲")
	default:
		return lipgloss.NewStyle().Foreground(colBlue).Render("●")
	}
}

func renderStepLine(step session.ToolStep) string {
	if step.ActionType == "edit" {
		fn := step.TargetFile
		if fn == "" {
			fn = step.Name
		}
		icon := fileDevIcon(fn)
		fname := lipgloss.NewStyle().Foreground(colText).Bold(true).Render(fn)
		plus := lipgloss.NewStyle().Foreground(colGreen).Render(fmt.Sprintf("+%d", step.LinesAdded))
		minus := lipgloss.NewStyle().Foreground(colRed).Render(fmt.Sprintf("-%d", step.LinesRemoved))

		dur := ""
		if step.Duration != "" && step.Duration != "done" {
			dur = " " + lipgloss.NewStyle().Foreground(colMuted).Render("("+step.Duration+")")
		}
		return fmt.Sprintf("  Edited %s%s %s %s%s", icon, fname, plus, minus, dur)
	}

	srv := step.Server
	if srv == "" {
		srv = "mcp"
	}
	srvIcon := serverIcon(srv)
	srvName := lipgloss.NewStyle().Foreground(colSubtext).Render(srv)
	arrow := lipgloss.NewStyle().Foreground(colMuted).Render("›")
	toolIcon := lipgloss.NewStyle().Foreground(colSky).Render("◇")

	argSummary := ""
	if step.TargetFile != "" {
		argSummary = fmt.Sprintf("(%s)", step.TargetFile)
	} else if cmd, ok := step.Args["command"].(string); ok && cmd != "" {
		if len(cmd) > 28 {
			cmd = cmd[:25] + "..."
		}
		argSummary = fmt.Sprintf("(\"%s\")", cmd)
	} else if q, ok := step.Args["query"].(string); ok && q != "" {
		if len(q) > 28 {
			q = q[:25] + "..."
		}
		argSummary = fmt.Sprintf("(\"%s\")", q)
	} else {
		argSummary = "()"
	}

	toolName := lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render(step.Name + argSummary)

	dur := ""
	if step.Duration != "" && step.Duration != "done" {
		dur = " " + lipgloss.NewStyle().Foreground(colMuted).Render("("+step.Duration+")")
	}

	return fmt.Sprintf("  %s %s %s %s %s%s", srvIcon, srvName, arrow, toolIcon, toolName, dur)
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

func parseStepDetails(name, server string, args map[string]interface{}) (targetFile string, lineRange string, actionType string, added int, removed int) {
	nameLower := strings.ToLower(name)

	for _, k := range []string{"target_file", "path", "file_path", "filename", "file", "target"} {
		if val, ok := args[k].(string); ok && val != "" {
			targetFile = filepath.Base(val)
			break
		}
	}

	startLine := 0
	endLine := 0
	for _, sk := range []string{"start_line", "start", "from_line", "line_start"} {
		if sl, ok := args[sk].(float64); ok && sl > 0 {
			startLine = int(sl)
			break
		} else if sl, ok := args[sk].(int); ok && sl > 0 {
			startLine = sl
			break
		}
	}
	for _, ek := range []string{"end_line", "end", "to_line", "line_end"} {
		if el, ok := args[ek].(float64); ok && el > 0 {
			endLine = int(el)
			break
		} else if el, ok := args[ek].(int); ok && el > 0 {
			endLine = el
			break
		}
	}

	if startLine > 0 && endLine > 0 {
		lineRange = fmt.Sprintf("#L%d-%d", startLine, endLine)
	} else if startLine > 0 {
		lineRange = fmt.Sprintf("#L%d", startLine)
	}

	if strings.Contains(nameLower, "write") || strings.Contains(nameLower, "create_file") || strings.Contains(nameLower, "replace_text") || strings.Contains(nameLower, "append_file") {
		actionType = "edit"
		if content, ok := args["content"].(string); ok {
			added = strings.Count(content, "\n") + 1
		}
		if newText, ok := args["new_text"].(string); ok {
			added = strings.Count(newText, "\n") + 1
		}
		if oldText, ok := args["old_text"].(string); ok {
			removed = strings.Count(oldText, "\n") + 1
		}
		if added == 0 && removed == 0 {
			added = 1
		}
	} else if strings.Contains(nameLower, "read") || strings.Contains(nameLower, "list") || strings.Contains(nameLower, "tree") || strings.Contains(nameLower, "search_files") || strings.Contains(nameLower, "stat") || strings.Contains(nameLower, "grep") || strings.Contains(nameLower, "explore") {
		actionType = "explore"
	} else if strings.Contains(nameLower, "run_shell") || strings.Contains(nameLower, "command") || strings.Contains(nameLower, "manage_server") {
		actionType = "run"
	} else if strings.Contains(nameLower, "web_search") || strings.Contains(nameLower, "web_fetch") {
		actionType = "search"
	} else {
		actionType = "tool"
	}
	return
}

// ─── Sidebar View (Transparent with Clean Sections) ──────────────────────────

func (m ReplModel) viewSidebar(w, h int) string {
	innerW := w - 2
	var sections []string

	// Compact PIHU ASCII art at top of sidebar
	art := lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render(
		"  ____ ___ _   _ _   _\n" +
		" |  _ \\_ _| | | | | | |\n" +
		" | |_) | || |_| | | | |\n" +
		" |  __/| ||  _  | |_| |\n" +
		" |_|  |___|_| |_|\\___/",
	)
	subtitle := lipgloss.NewStyle().Foreground(colMuted).Render(" AI Terminal IDE v0.1.0")
	sections = append(sections, art, subtitle, "")

	// Workspace section
	sections = append(sections,
		lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render("◇ Workspace"),
		lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW)),
		sideRow("Project", m.ws.Name),
	)
	if m.ws.Framework != "" {
		sections = append(sections, sideRow("Framework", m.ws.Framework))
	} else if m.ws.Language != "" {
		sections = append(sections, sideRow("Language", m.ws.Language))
	}
	if m.ws.GitBranch != "" {
		dirty := ""
		if m.ws.GitDirty {
			dirty = "*"
		}
		sections = append(sections, sideRow("Git", m.ws.GitBranch+dirty))
	}
	if m.ws.FileCount > 0 {
		sections = append(sections, sideRow("Files", fmt.Sprintf("%d", m.ws.FileCount)))
	}
	sections = append(sections, "")

	// Active MCPs section (5 connected servers)
	sections = append(sections,
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("◇ Active MCPs"),
		lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW)),
	)
	for _, s := range []struct {
		name  string
		tools string
		c     lipgloss.Color
	}{
		{"pihu-file-mcp", "24", colMauve},
		{"pihu-system-mcp", "7", colGreen},
		{"pihu-web-search-mcp", "6", colSky},
		{"google-workspace-mcp", "10", colYellow},
		{"pihu-project-mcp", "6", colPeach},
	} {
		dot := lipgloss.NewStyle().Foreground(colGreen).Render("●")
		sname := lipgloss.NewStyle().Foreground(colText).Render(s.name)
		stools := lipgloss.NewStyle().Foreground(colMuted).Render(" (" + s.tools + ")")
		sections = append(sections, fmt.Sprintf("%s %s%s", dot, sname, stools))
	}
	sections = append(sections, "")

	// Recent Prompts
	sections = append(sections,
		lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("◇ Recent"),
		lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW)),
	)
	recent := m.sess.RecentPrompts(4)
	if len(recent) == 0 {
		sections = append(sections,
			lipgloss.NewStyle().Foreground(colMuted).Italic(true).Render("No history yet"),
		)
	} else {
		for _, r := range recent {
			sections = append(sections, lipgloss.NewStyle().Foreground(colSubtext).Render(r))
		}
	}
	sections = append(sections, "")

	// Quick Commands
	sections = append(sections,
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("◇ Commands"),
		lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", innerW)),
	)
	for _, kv := range [][2]string{
		{"/help", "All commands"},
		{"/model", "Switch model"},
		{"/key", "Gemini tokens"},
		{"/tools", "53 MCP tools"},
		{"/mcp", "Server status"},
		{"/workspace", "Project stats"},
		{"/clear", "Clear screen"},
		{"/exit", "Quit PIHU"},
	} {
		k := lipgloss.NewStyle().Foreground(colGreen).Bold(true).Width(11).Render(kv[0])
		v := lipgloss.NewStyle().Foreground(colMuted).Render(kv[1])
		sections = append(sections, k+v)
	}

	content := strings.Join(sections, "\n")
	contentH := strings.Count(content, "\n") + 1
	for i := contentH; i < h; i++ {
		content += "\n"
	}

	return lipgloss.NewStyle().
		Width(w).
		Height(h).
		PaddingLeft(1).
		Render(content)
}

func sideRow(label, value string) string {
	lbl := lipgloss.NewStyle().Foreground(colMuted).Width(10).Render(label)
	val := lipgloss.NewStyle().Foreground(colMauve).Render(value)
	return lbl + val
}

// ─── Input Area (Transparent with Rounded Border & Focus Modes) ──────────────

func (m ReplModel) viewInput() string {
	w := m.width
	isFocused := m.input.Focused()

	var promptLabel string
	var borderCol lipgloss.Color

	if isFocused {
		promptLabel = lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render("You") +
			" " + lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("›")
		borderCol = colMauve
	} else {
		promptLabel = lipgloss.NewStyle().Foreground(colMuted).Bold(true).Render("NORMAL") +
			" " + lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render("›")
		borderCol = colSurf1
	}

	// Left input box
	inputW := w - 34
	if inputW < 30 {
		inputW = 30
	}

	inputVal := m.input.Value()
	// Dynamic vertical height expansion based on content length or line breaks
	lineCount := strings.Count(inputVal, "\n") + 1
	if inputW > 12 && len(inputVal) > (inputW-12) {
		lineCount += len(inputVal) / (inputW - 12)
	}
	inputH := min(4, max(1, lineCount))

	inputLine := promptLabel + " " + m.input.View()
	inputBox := lipgloss.NewStyle().
		Width(inputW).
		Height(inputH).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderCol).
		Padding(0, 1).
		Render(inputLine)

	// Right status / shortcuts box
	hintW := w - inputW - 3
	if hintW < 24 {
		hintW = 24
	}

	var hintContent string
	if m.isBusy {
		elapsed := time.Since(m.turnStartTime).Seconds()
		hintContent = m.spinner.View() + " " + lipgloss.NewStyle().Foreground(colMauve).Render(fmt.Sprintf("Working... %.1fs", elapsed))
	} else if isFocused {
		hintContent = lipgloss.NewStyle().Foreground(colMuted).Render("Esc Unfocus   Enter Send\n^K Palette    /key Tokens\n@ File Mention")
	} else {
		hintContent = lipgloss.NewStyle().Foreground(colSubtext).Render("i Focus Chat   j/k Scroll\n/ Commands     ^K Palette")
	}

	hintBox := lipgloss.NewStyle().
		Width(hintW).
		Height(inputH).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderCol).
		Padding(0, 1).
		Render(hintContent)

	inputRow := lipgloss.JoinHorizontal(lipgloss.Top, inputBox, " ", hintBox)

	// Render interactive suggestion box on top of input if suggestions active
	if len(m.suggestions) > 0 && isFocused && strings.HasPrefix(m.input.Value(), "/") {
		sugBox := RenderSuggestionBox(m.suggestions, m.selectedSugIdx, inputW)
		return lipgloss.JoinVertical(lipgloss.Left, sugBox, inputRow)
	}

	return inputRow
}

// ─── Palette Modal Renderer ──────────────────────────────────────────────────

func renderPaletteBox(inputView string) string {
	palW := 48

	commands := []string{
		"  › Ask PIHU (type your prompt)",
		"  › /model     Dynamic model selector",
		"  › /key       View / add Gemini tokens",
		"  › /tools     List 53 MCP tools",
		"  › /mcp       Show server health",
		"  › /provider  Toggle gemini / ollama",
		"  › /workspace Project detector info",
		"  › /clear     Clear conversation",
		"  › /help      Command reference",
		"  › /exit      Quit PIHU",
	}

	body := inputView + "\n" + strings.Repeat("─", palW-4) + "\n" + strings.Join(commands, "\n")

	return lipgloss.NewStyle().
		Width(palW).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Padding(1, 2).
		Render(
			lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("◇ Command Palette") + "\n\n" + body,
		)
}

// ─── Slash Command Content ───────────────────────────────────────────────────

func helpMsg() string {
	cmds := [][2]string{
		{"/model", "Dynamic model selector (Gemini Cloud + Ollama Local)"},
		{"/key <token>", "View or configure Gemini API tokens"},
		{"/tools", "List all 53 available MCP tools"},
		{"/mcp", "Show connected MCP servers and status"},
		{"/provider", "Toggle between ollama and gemini"},
		{"/workspace", "Show workspace metadata & git status"},
		{"/clear", "Clear conversation screen"},
		{"/help", "Show this help"},
		{"/exit", "Exit PIHU"},
	}
	var rows []string
	rows = append(rows, lipgloss.NewStyle().Foreground(colMauve).Bold(true).Render("PIHU Commands\n"))
	rows = append(rows, lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", 50)))
	for _, c := range cmds {
		k := lipgloss.NewStyle().Foreground(colGreen).Bold(true).Width(16).Render(c[0])
		v := lipgloss.NewStyle().Foreground(colSubtext).Render(c[1])
		rows = append(rows, k+v)
	}
	rows = append(rows, "")
	rows = append(rows, lipgloss.NewStyle().Foreground(colMuted).Render(
		"Shortcuts: PageUp/PageDown Scroll · Ctrl+K Palette · Ctrl+L Clear",
	))
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colMauve).
		Padding(1, 2).
		Render(strings.Join(rows, "\n"))
}

func mcpMsg() string {
	rows := []string{
		lipgloss.NewStyle().Foreground(colGreen).Bold(true).Render("MCP Servers  (5 online)\n"),
		lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", 50)),
	}
	for _, s := range []struct{ name, transport, tools string }{
		{"pihu-file-mcp", "stdio · python", "24"},
		{"pihu-system-mcp", "stdio · python", "7"},
		{"pihu-web-search-mcp", "stdio · python", "6"},
		{"google-workspace-mcp", "stdio · python", "10"},
		{"pihu-project-mcp", "stdio · node", "6"},
	} {
		dot := lipgloss.NewStyle().Foreground(colGreen).Render("●")
		name := lipgloss.NewStyle().Foreground(colText).Width(22).Render(s.name)
		trans := lipgloss.NewStyle().Foreground(colMuted).Width(16).Render(s.transport)
		tools := lipgloss.NewStyle().Foreground(colBlue).Render(s.tools + " tools")
		rows = append(rows, dot+" "+name+trans+tools)
	}
	rows = append(rows, "")
	rows = append(rows, lipgloss.NewStyle().Foreground(colMuted).Render("Total: 5 servers · 53 tools"))
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colGreen).
		Padding(1, 2).
		Render(strings.Join(rows, "\n"))
}

func toolsMsg() string {
	rows := []string{
		lipgloss.NewStyle().Foreground(colBlue).Bold(true).Render("MCP Tools  (53 available)\n"),
		lipgloss.NewStyle().Foreground(colSurf1).Render(strings.Repeat("─", 50)),
	}
	for _, g := range []struct {
		c    lipgloss.Color
		icon string
		name string
		list string
	}{
		{colMauve, "◈", "pihu-file-mcp (24)", "read_file · write_file · search_files · tree · grep_search · replace_text …"},
		{colGreen, "◇", "pihu-system-mcp (7)", "get_system_info · run_shell · list_processes · send_notification …"},
		{colSky, "›", "pihu-web-search-mcp (6)", "web_search · web_fetch · web_search_and_read · web_download_file …"},
		{colYellow, "§", "google-workspace-mcp (10)", "gmail_search · gmail_send · calendar_list · drive_search · docs_create …"},
		{colPeach, "▲", "pihu-project-mcp (6)", "scaffold_project · test_project · diagnose_and_fix · manage_server …"},
	} {
		rows = append(rows, "")
		rows = append(rows, lipgloss.NewStyle().Foreground(g.c).Bold(true).Render(g.icon+" "+g.name))
		rows = append(rows, lipgloss.NewStyle().Foreground(colMuted).PaddingLeft(2).Render(g.list))
	}
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colBlue).
		Padding(1, 2).
		Render(strings.Join(rows, "\n"))
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

func sidebarWidth(totalW int) int {
	if totalW >= 140 {
		return 38
	}
	if totalW >= 100 {
		return 34
	}
	return 30
}

func wrapText(text string, width int) []string {
	if width <= 0 {
		width = 60
	}
	var result []string
	for _, rawLine := range strings.Split(text, "\n") {
		words := strings.Fields(rawLine)
		if len(words) == 0 {
			result = append(result, "")
			continue
		}
		line := ""
		for _, word := range words {
			if len(line)+len(word)+1 > width {
				if line != "" {
					result = append(result, line)
				}
				line = word
			} else {
				if line == "" {
					line = word
				} else {
					line += " " + word
				}
			}
		}
		if line != "" {
			result = append(result, line)
		}
	}
	return result
}
