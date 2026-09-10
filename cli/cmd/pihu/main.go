package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"pihu/cli/internal/ui"

	tea "github.com/charmbracelet/bubbletea"
)

func main() {
	providerFlag := flag.String("provider", "", "LLM provider: ollama or gemini")
	modelFlag := flag.String("model", "", "Model name (e.g. qwen3:4b, gemini-3.6-flash)")
	flag.Parse()

	args := flag.Args()

	cwd, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting current directory: %v\n", err)
		os.Exit(1)
	}
	projectDir := findProjectRoot(cwd)

	// If prompt is provided via positional arguments, run single task execution mode
	if len(args) > 0 {
		prompt := strings.Join(args, " ")
		runSingleTask(prompt, projectDir, *providerFlag, *modelFlag)
		return
	}

	// Otherwise, enter PIHU Interactive REPL Mode
	runREPL(projectDir, *providerFlag, *modelFlag)
}

func runSingleTask(prompt, projectDir, provider, model string) {
	m := ui.NewModel(prompt, projectDir, provider, model)

	var p *tea.Program
	if !isTerminal() {
		p = tea.NewProgram(m, tea.WithoutRenderer(), tea.WithInput(nil))
	} else {
		p = tea.NewProgram(m)
	}

	finalModel, err := p.Run()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error running PIHU CLI: %v\n", err)
		os.Exit(1)
	}

	// Always print final rendered view to stdout so output remains visible after exit
	if finalM, ok := finalModel.(ui.Model); ok {
		fmt.Println(finalM.View())
	}
}

func runREPL(projectDir, initialProvider, initialModel string) {
	currentProvider := initialProvider
	if currentProvider == "" {
		currentProvider = "ollama"
	}
	currentModel := initialModel
	if currentModel == "" {
		if currentProvider == "gemini" {
			currentModel = "gemini-3.6-flash"
		} else {
			currentModel = "qwen3:4b"
		}
	}

	fmt.Println(ui.HeaderStyle.Render("PIHU Interactive REPL Mode\nPersonalized Intelligent Human Utility"))
	fmt.Println(ui.SubtitleStyle.Render("Type a task prompt to execute, or use slash commands:"))
	fmt.Println(ui.SubtitleStyle.Render("  /model     - Switch between Ollama & Gemini models"))
	fmt.Println(ui.SubtitleStyle.Render("  /provider  - Toggle between Ollama & Gemini providers"))
	fmt.Println(ui.SubtitleStyle.Render("  /clear     - Clear terminal screen"))
	fmt.Println(ui.SubtitleStyle.Render("  /exit      - Exit REPL"))
	fmt.Println()

	scanner := bufio.NewScanner(os.Stdin)

	for {
		promptLabel := ui.TitleStyle.Render(fmt.Sprintf("pihu (%s:%s) > ", currentProvider, currentModel))
		fmt.Print(promptLabel)

		if !scanner.Scan() {
			break
		}

		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		switch {
		case line == "/exit" || line == "/quit":
			fmt.Println(ui.SubtitleStyle.Render("Goodbye!"))
			return

		case line == "/clear":
			fmt.Print("\033[H\033[2J")

		case line == "/provider":
			if currentProvider == "ollama" {
				currentProvider = "gemini"
				currentModel = "gemini-3.6-flash"
			} else {
				currentProvider = "ollama"
				currentModel = "qwen3:4b"
			}
			fmt.Println(ui.SuccessIcon.Render(fmt.Sprintf("Switched provider to %s (%s)", currentProvider, currentModel)))

		case line == "/model" || strings.HasPrefix(line, "/model "):
			cmdParts := strings.Fields(line)
			if len(cmdParts) > 1 {
				currentModel = cmdParts[1]
				if strings.HasPrefix(currentModel, "gemini") {
					currentProvider = "gemini"
				} else {
					currentProvider = "ollama"
				}
				fmt.Println(ui.SuccessIcon.Render(fmt.Sprintf("Model set to %s (%s)", currentModel, currentProvider)))
			} else {
				// Interactive Model Selector Menu
				fmt.Println(ui.TimelineCategory.Render("\nAvailable Models:"))
				fmt.Println("  1) qwen3:4b                   [Ollama local]")
				fmt.Println("  2) gemma3:4b                  [Ollama local]")
				fmt.Println("  3) llama3.1:8b-instruct-q8_0  [Ollama local]")
				fmt.Println("  4) gemini-3.6-flash           [Gemini cloud]")
				fmt.Println("  5) gemini-2.5-flash           [Gemini cloud]")
				fmt.Print(ui.TaskLabelStyle.Render("Select option (1-5) or enter custom model name: "))

				if scanner.Scan() {
					choice := strings.TrimSpace(scanner.Text())
					switch choice {
					case "1":
						currentProvider = "ollama"
						currentModel = "qwen3:4b"
					case "2":
						currentProvider = "ollama"
						currentModel = "gemma3:4b"
					case "3":
						currentProvider = "ollama"
						currentModel = "llama3.1:8b-instruct-q8_0"
					case "4":
						currentProvider = "gemini"
						currentModel = "gemini-3.6-flash"
					case "5":
						currentProvider = "gemini"
						currentModel = "gemini-2.5-flash"
					default:
						if choice != "" {
							currentModel = choice
							if strings.HasPrefix(choice, "gemini") {
								currentProvider = "gemini"
							} else {
								currentProvider = "ollama"
							}
						}
					}
					fmt.Println(ui.SuccessIcon.Render(fmt.Sprintf("Active model updated to %s (%s)\n", currentModel, currentProvider)))
				}
			}

		default:
			// Execute Task
			fmt.Println()
			runSingleTask(line, projectDir, currentProvider, currentModel)
			fmt.Println()
		}
	}
}

func isTerminal() bool {
	fi, err := os.Stdout.Stat()
	if err != nil {
		return false
	}
	return (fi.Mode() & os.ModeCharDevice) != 0
}

func findProjectRoot(start string) string {
	curr := start
	for {
		if _, err := os.Stat(filepath.Join(curr, "pyproject.toml")); err == nil {
			return curr
		}
		parent := filepath.Dir(curr)
		if parent == curr {
			break
		}
		curr = parent
	}
	return start
}
