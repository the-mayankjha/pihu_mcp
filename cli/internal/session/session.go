// Package session manages conversation history and session state.
package session

import (
	"fmt"
	"math/rand"
	"time"
)

// Role identifies who sent a message.
type Role int

const (
	RoleUser   Role = iota
	RolePihu        // Agent response
	RoleTool        // Inline tool step
	RoleSystem      // System / info message
	RoleDiff        // File diff block
	RoleApproval    // Permission request
)

// ToolStep represents one tool call inside an agent turn.
type ToolStep struct {
	Name         string
	Server       string
	Args         map[string]interface{}
	Output       string
	Duration     string
	Done         bool
	Error        bool
	StartedAt    time.Time
	TargetFile   string
	LineRange    string
	LinesAdded   int
	LinesRemoved int
	ActionType   string // "explore", "edit", "run", "search", "tool"
}

// DiffHunk is one changed file shown in a diff block.
type DiffHunk struct {
	Path    string
	Before  string
	After   string
	Added   int
	Removed int
}

// ApprovalRequest is shown when PIHU needs permission to run something.
type ApprovalRequest struct {
	Command     string
	Reason      string
	RiskLevel   RiskLevel
	Answered    bool
	Approved    bool
}

// RiskLevel categorizes how dangerous a tool call is.
type RiskLevel int

const (
	RiskSafe     RiskLevel = iota // read, search, git status
	RiskModerate                  // write files, install packages
	RiskDangerous                 // delete, reset, sudo
)

func (r RiskLevel) String() string {
	switch r {
	case RiskSafe:
		return "SAFE"
	case RiskModerate:
		return "MODERATE"
	case RiskDangerous:
		return "DANGEROUS"
	}
	return "UNKNOWN"
}

// Message is one entry in the conversation.
type Message struct {
	Role      Role
	Text      string
	Timestamp time.Time

	// Used when Role == RolePihu
	Steps        []ToolStep
	NeededTools  []string
	TurnDuration time.Duration

	// Used when Role == RoleDiff
	Diffs []DiffHunk

	// Used when Role == RoleApproval
	Approval *ApprovalRequest

	// Metadata
	TokensUsed int
	ModelName  string
	Duration   time.Duration
}

func (m Message) TimeStr() string {
	return m.Timestamp.Format("15:04:05")
}

// Session holds the full conversation.
type Session struct {
	ID        string
	StartedAt time.Time
	Messages  []Message
	WorkDir   string

	// Running stats
	TotalTokens int
	TotalTools  int
	TotalTime   time.Duration
}

// New creates a fresh session.
func New(workDir string) *Session {
	return &Session{
		ID:        randomID(),
		StartedAt: time.Now(),
		WorkDir:   workDir,
		Messages:  []Message{},
	}
}

// AddUser appends a user message.
func (s *Session) AddUser(text string) *Message {
	msg := Message{
		Role:      RoleUser,
		Text:      text,
		Timestamp: time.Now(),
	}
	s.Messages = append(s.Messages, msg)
	return &s.Messages[len(s.Messages)-1]
}

// StartAgentTurn begins a new Pihu response message (steps accumulate into it).
func (s *Session) StartAgentTurn() *Message {
	msg := Message{
		Role:      RolePihu,
		Timestamp: time.Now(),
		Steps:     []ToolStep{},
	}
	s.Messages = append(s.Messages, msg)
	return &s.Messages[len(s.Messages)-1]
}

// AddSystem appends a system info line.
func (s *Session) AddSystem(text string) {
	s.Messages = append(s.Messages, Message{
		Role:      RoleSystem,
		Text:      text,
		Timestamp: time.Now(),
	})
}

// RecentPrompts returns the last N user messages as strings.
func (s *Session) RecentPrompts(n int) []string {
	var out []string
	for i := len(s.Messages) - 1; i >= 0 && len(out) < n; i-- {
		if s.Messages[i].Role == RoleUser {
			txt := s.Messages[i].Text
			if len(txt) > 44 {
				txt = txt[:41] + "..."
			}
			out = append(out, fmt.Sprintf("%s  %s", s.Messages[i].TimeStr(), txt))
		}
	}
	return out
}

func randomID() string {
	return fmt.Sprintf("%x", rand.Int31())[:7]
}
