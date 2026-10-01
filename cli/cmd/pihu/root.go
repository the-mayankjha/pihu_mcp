package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"pihu/cli/internal/ui"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"
)

var (
	providerFlag string
	modelFlag    string
	jsonFlag     bool
	verboseFlag  bool
)

var rootCmd = &cobra.Command{
	Use:   "pihu [prompt]",
	Short: "PIHU — Personalized Intelligent Human Utility AI Agent & MCP Operating Environment",
	Long: ui.RenderAsciiArt() + "\n\n" +
		"PIHU is an autonomous desktop and coding agent runtime powered by the Model Context Protocol (MCP).\n" +
		"Supports dual LLMs (Google Gemini & local Ollama), 5 builtin MCP servers, and 53 tools.",
	Args: cobra.ArbitraryArgs,
	Run: func(cmd *cobra.Command, args []string) {
		cwd, err := os.Getwd()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error getting current directory: %v\n", err)
			os.Exit(1)
		}
		projectDir := findProjectRoot(cwd)

		// If prompt is passed via positional arguments, execute single task
		if len(args) > 0 {
			prompt := strings.Join(args, " ")
			runSingleTask(prompt, projectDir, providerFlag, modelFlag)
			return
		}

		// Otherwise, start Interactive Bubble Tea REPL Agent
		runInteractiveREPL(projectDir, providerFlag, modelFlag)
	},
}

func init() {
	rootCmd.PersistentFlags().StringVarP(&providerFlag, "provider", "p", "", "LLM provider: 'gemini' (cloud) or 'ollama' (local)")
	rootCmd.PersistentFlags().StringVarP(&modelFlag, "model", "m", "", "Model name (e.g. gemini-2.0-flash, qwen3:4b)")
	rootCmd.PersistentFlags().BoolVar(&jsonFlag, "json", false, "Emit events as JSON-Lines only (for external IPC/integrations)")
	rootCmd.PersistentFlags().BoolVarP(&verboseFlag, "verbose", "v", false, "Enable verbose output and tool traces")

	mcpCmd.AddCommand(mcpSearchCmd)
	mcpCmd.AddCommand(mcpInfoCmd)
	mcpCmd.AddCommand(mcpInstallCmd)
	mcpCmd.AddCommand(mcpListCmd)
	mcpCmd.AddCommand(mcpRemoveCmd)
	mcpCmd.AddCommand(mcpUpdateCmd)
	mcpCmd.AddCommand(mcpDoctorCmd)
	mcpCmd.AddCommand(mcpRefreshCmd)

	mcpWhatsappCmd.AddCommand(mcpWhatsappAuthCmd)
	mcpWhatsappCmd.AddCommand(mcpWhatsappStatusCmd)
	mcpWhatsappCmd.AddCommand(mcpWhatsappLogoutCmd)
	mcpWhatsappCmd.AddCommand(mcpWhatsappSendCmd)
	mcpCmd.AddCommand(mcpWhatsappCmd)

	rootCmd.AddCommand(chatCmd)
	rootCmd.AddCommand(runCmd)
	rootCmd.AddCommand(toolsCmd)
	rootCmd.AddCommand(mcpCmd)
	rootCmd.AddCommand(mcpWhatsappCmd)
	rootCmd.AddCommand(versionCmd)
}

func runInteractiveREPL(projectDir, provider, model string) {
	repl := ui.NewReplModel(projectDir, provider, model)
	p := tea.NewProgram(repl, tea.WithAltScreen())

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error running PIHU REPL: %v\n", err)
		os.Exit(1)
	}
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
		fmt.Fprintf(os.Stderr, "Error executing task: %v\n", err)
		os.Exit(1)
	}

	if finalM, ok := finalModel.(ui.Model); ok {
		fmt.Println(finalM.View())
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
