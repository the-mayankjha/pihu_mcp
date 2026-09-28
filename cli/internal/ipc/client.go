package ipc

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"

	"pihu/cli/internal/events"
)

// Client launches and manages the Python runtime IPC process.
type Client struct {
	projectDir string
}

func NewClient(projectDir string) *Client {
	return &Client{
		projectDir: projectDir,
	}
}

func (c *Client) resolvePythonCommand(args ...string) *exec.Cmd {
	// 1. Check local virtualenv .venv/bin/python3
	venvPy := filepath.Join(c.projectDir, ".venv", "bin", "python3")
	if fi, err := os.Stat(venvPy); err == nil && !fi.IsDir() {
		cmdArgs := append([]string{"-m", "pihu.main"}, args...)
		cmd := exec.Command(venvPy, cmdArgs...)
		cmd.Dir = c.projectDir
		return cmd
	}

	// 2. Check uv in PATH
	if uvPath, err := exec.LookPath("uv"); err == nil {
		cmdArgs := append([]string{"run", "python", "-m", "pihu.main"}, args...)
		cmd := exec.Command(uvPath, cmdArgs...)
		cmd.Dir = c.projectDir
		return cmd
	}

	// 3. Check pihu executable in PATH
	if pihuPath, err := exec.LookPath("pihu"); err == nil {
		cmd := exec.Command(pihuPath, args...)
		cmd.Dir = c.projectDir
		return cmd
	}

	// 4. Fallback to system python3
	cmdArgs := append([]string{"-m", "pihu.main"}, args...)
	cmd := exec.Command("python3", cmdArgs...)
	cmd.Dir = c.projectDir
	return cmd
}

// StreamTask launches python -m pihu.main --json "<prompt>" and streams events to the returned channel.
func (c *Client) StreamTask(prompt, provider, model string) (<-chan events.AgentEvent, <-chan error, error) {
	eventChan := make(chan events.AgentEvent, 100)
	errChan := make(chan error, 1)

	var subArgs []string
	subArgs = append(subArgs, "--json", prompt)
	if provider != "" {
		subArgs = append(subArgs, "--provider", provider)
	}
	if model != "" {
		subArgs = append(subArgs, "--model", model)
	}

	cmd := c.resolvePythonCommand(subArgs...)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get stdout pipe: %w", err)
	}

	stderr, _ := cmd.StderrPipe()

	if err := cmd.Start(); err != nil {
		return nil, nil, fmt.Errorf("failed to start Python runtime process (%s): %w", cmd.Path, err)
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

		if stderr != nil {
			_, _ = io.ReadAll(stderr)
		}

		_ = cmd.Wait()
	}()

	return eventChan, errChan, nil
}
