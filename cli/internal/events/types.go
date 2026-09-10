package events

// AgentEvent matches the JSON event emitted by the Python runtime over IPC.
type AgentEvent struct {
	Type      string                 `json:"type"`
	TaskID    string                 `json:"task_id,omitempty"`
	SessionID string                 `json:"session_id,omitempty"`
	Timestamp string                 `json:"timestamp"`
	Component string                 `json:"component"`
	Status    string                 `json:"status"`
	Message   string                 `json:"message,omitempty"`
	Details   map[string]interface{} `json:"details,omitempty"`
}
