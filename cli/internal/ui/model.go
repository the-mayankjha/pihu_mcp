package ui

import (
	"fmt"
	"strings"
	"time"

	"pihu/cli/internal/events"
	"pihu/cli/internal/ipc"

	tea "github.com/charmbracelet/bubbletea"
)

type state int

const (
	stateRunning state = iota
	stateCompleted
	stateError
)

type eventMsg events.AgentEvent
type streamDoneMsg struct{}
type errMsg error

// streamStartedMsg carries the channels created by StreamTask back into Update,
// so they are stored on the authoritative Model — not a closure copy.
type streamStartedMsg struct {
	eventChan <-chan events.AgentEvent
	errChan   <-chan error
}

type Model struct {
	prompt        string
	state         state
	client        *ipc.Client
	eventChan     <-chan events.AgentEvent
	errChan       <-chan error
	provider      string
	targetModel   string
	timeline      []TimelineEntry
	result        string
	modelSelected string
	toolsUsed     []string
	err           error
	startTime     time.Time
	elapsed       time.Duration
	width         int
	height        int
}

type TimelineEntry struct {
	Category string
	Status   string // "success", "running", "error", "info"
	Text     string
	Detail   string
}

func NewModel(prompt string, projectDir string, provider string, targetModel string) Model {
	return Model{
		prompt:      prompt,
		provider:    provider,
		targetModel: targetModel,
		state:       stateRunning,
		client:      ipc.NewClient(projectDir),
		timeline:    make([]TimelineEntry, 0),
		startTime:   time.Now(),
		width:       80,
	}
}

// Init launches the Python subprocess. It returns a Cmd that sends back
// streamStartedMsg so that Update can store the channels on the real Model.
func (m Model) Init() tea.Cmd {
	client := m.client
	prompt := m.prompt
	provider := m.provider
	targetModel := m.targetModel

	return func() tea.Msg {
		eventChan, errChan, err := client.StreamTask(prompt, provider, targetModel)
		if err != nil {
			return errMsg(err)
		}
		return streamStartedMsg{eventChan: eventChan, errChan: errChan}
	}
}

func listenForNextEvent(eventChan <-chan events.AgentEvent) tea.Cmd {
	return func() tea.Msg {
		if eventChan == nil {
			return streamDoneMsg{}
		}

		ev, ok := <-eventChan
		if !ok {
			return streamDoneMsg{}
		}
		return eventMsg(ev)
	}
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case streamStartedMsg:
		// Now we store channels on the real Model (not a closure copy).
		m.eventChan = msg.eventChan
		m.errChan = msg.errChan
		return m, listenForNextEvent(m.eventChan)

	case eventMsg:
		ev := events.AgentEvent(msg)
		m.handleAgentEvent(ev)
		return m, listenForNextEvent(m.eventChan)

	case streamDoneMsg:
		if m.state == stateRunning {
			m.state = stateCompleted
		}
		if m.elapsed == 0 {
			m.elapsed = time.Since(m.startTime)
		}
		return m, tea.Quit

	case errMsg:
		m.err = error(msg)
		m.state = stateError
		return m, tea.Quit
	}

	return m, nil
}

func (m *Model) handleAgentEvent(ev events.AgentEvent) {
	switch ev.Type {
	case "TASK_STARTED":
		m.addTimeline("Task", "success", "Intent understood", "")

	case "CONTEXT_LOADING":
		m.addTimeline("Context", "success", "Loaded environment & project context", "")

	case "MODEL_SELECTED":
		if prov, ok := ev.Details["provider"].(string); ok {
			m.modelSelected = prov
			modelName, _ := ev.Details["model"].(string)
			if modelName != "" {
				m.modelSelected = fmt.Sprintf("%s/%s", prov, modelName)
			}
			m.addTimeline("Model", "success", fmt.Sprintf("Selected: %s", m.modelSelected), "")
		}

	case "TOOL_DISCOVERED":
		if tools, ok := ev.Details["tools"].([]interface{}); ok {
			server, _ := ev.Details["server"].(string)
			m.addTimeline("MCP Tools", "success", fmt.Sprintf("Discovered %d tools from '%s'", len(tools), server), "")
		}

	case "TOOL_STARTED":
		if tool, ok := ev.Details["tool"].(string); ok {
			m.addTimeline("Execution", "running", fmt.Sprintf("Executing %s...", tool), "")
		}

	case "TOOL_COMPLETED":
		if tool, ok := ev.Details["tool"].(string); ok {
			m.toolsUsed = append(m.toolsUsed, tool)
			preview := ""
			if prev, ok := ev.Details["output_preview"].(string); ok {
				preview = prev
			}
			m.addTimeline("Execution", "success", fmt.Sprintf("Response from %s", tool), preview)
		}

	case "TASK_COMPLETED":
		if res, ok := ev.Details["result"].(string); ok {
			m.result = res
		}
		m.state = stateCompleted
		m.elapsed = time.Since(m.startTime)

	case "ERROR":
		m.addTimeline("Error", "error", ev.Message, "")

	case "MODEL_SWITCHED":
		from, _ := ev.Details["from"].(string)
		to, _ := ev.Details["to"].(string)
		m.addTimeline("Model", "info", fmt.Sprintf("Fallback: %s → %s", from, to), "")
	}
}

func (m *Model) addTimeline(category, status, text, detail string) {
	m.timeline = append(m.timeline, TimelineEntry{
		Category: category,
		Status:   status,
		Text:     text,
		Detail:   detail,
	})
}

func (m Model) View() string {
	var sb strings.Builder
	width := m.width
	if width <= 0 {
		width = 60
	}
	divider := DividerStyle.Render(strings.Repeat("─", width-4))

	// Header Box
	headerTitle := TitleStyle.Render("PIHU") + "\n" + SubtitleStyle.Render("Personalized Intelligent Human Utility")
	sb.WriteString(HeaderStyle.Render(headerTitle) + "\n\n")

	// Task Box
	sb.WriteString(TaskLabelStyle.Render("TASK") + "\n")
	sb.WriteString(TaskValueStyle.Render(m.prompt) + "\n\n")
	sb.WriteString(divider + "\n\n")

	// Timeline
	lastCategory := ""
	for _, entry := range m.timeline {
		if entry.Category != lastCategory {
			sb.WriteString(TimelineCategory.Render(entry.Category) + "\n")
			lastCategory = entry.Category
		}

		var icon string
		switch entry.Status {
		case "success":
			icon = SuccessIcon.Render("✓")
		case "running":
			icon = RunningIcon.Render("◐")
		case "error":
			icon = ErrorIcon.Render("✗")
		default:
			icon = ArrowIcon.Render("→")
		}

		sb.WriteString(TimelineItem.Render(fmt.Sprintf("  %s %s", icon, entry.Text)) + "\n")
		if entry.Detail != "" {
			sb.WriteString(TimelineDetail.Render(fmt.Sprintf("    ↳ %s", entry.Detail)) + "\n")
		}
	}

	// Result Section
	if m.result != "" {
		sb.WriteString("\n" + divider + "\n\n")
		resultBox := ResultHeaderStyle.Render("RESPONSE") + "\n\n" + m.result
		sb.WriteString(ResultCardStyle.Render(resultBox) + "\n")
	}

	// Error Section
	if m.err != nil {
		sb.WriteString("\n" + ErrorIcon.Render(fmt.Sprintf("Error: %v", m.err)) + "\n")
	}

	// Footer Bar
	sb.WriteString("\n" + divider + "\n")
	modelName := m.modelSelected
	if modelName == "" {
		modelName = "qwen3:4b"
	}
	toolCount := len(m.toolsUsed)
	elapsedSec := m.elapsed.Seconds()
	if elapsedSec == 0 && !m.startTime.IsZero() {
		elapsedSec = time.Since(m.startTime).Seconds()
	}

	footerStr := fmt.Sprintf("%s  ·  MCP  ·  %d tool(s)  ·  %.1fs", modelName, toolCount, elapsedSec)
	sb.WriteString(FooterStyle.Render(footerStr) + "\n")

	return sb.String()
}
