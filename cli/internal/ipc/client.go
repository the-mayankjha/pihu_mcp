package ipc

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"

	"pihu/cli/internal/events"
)

// Client launches and manages the Python runtime IPC process.
type Client struct {
	pythonPath string
	projectDir string
}

func NewClient(projectDir string) *Client {
	return &Client{
		pythonPath: "uv",
		projectDir: projectDir,
	}
}

// StreamTask launches python -m pihu.main --json "<prompt>" and streams events to the returned channel.
func (c *Client) StreamTask(prompt, provider, model string) (<-chan events.AgentEvent, <-chan error, error) {
	eventChan := make(chan events.AgentEvent, 50)
	errChan := make(chan error, 1)

	args := []string{"run", "python", "-m", "pihu.main", "--json", prompt}
	if provider != "" {
		args = append(args, "--provider", provider)
	}
	if model != "" {
		args = append(args, "--model", model)
	}

	cmd := exec.Command(c.pythonPath, args...)
	cmd.Dir = c.projectDir

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get stdout pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return nil, nil, fmt.Errorf("failed to start Python runtime process: %w", err)
	}

	go func() {
		defer close(eventChan)
		defer close(errChan)

		reader := bufio.NewReader(stdout)
		for {
			line, err := reader.ReadBytes('\n')
			if err != nil {
				if err != io.EOF {
					errChan <- err
				}
				break
			}

			if len(line) == 0 {
				continue
			}

			var ev events.AgentEvent
			if err := json.Unmarshal(line, &ev); err == nil && ev.Type != "" {
				eventChan <- ev
			}
		}

		_ = cmd.Wait()
	}()

	return eventChan, errChan, nil
}
