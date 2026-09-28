// Package workspace provides project-level detection and metadata.
// When PIHU launches, it scans the working directory to understand
// what kind of project it's operating in — language, framework, git state, etc.
package workspace

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Info holds all detected metadata about the current workspace.
type Info struct {
	RootDir     string
	Name        string
	Language    string
	Framework   string
	PackageMgr  string
	GitBranch   string
	GitDirty    bool
	FileCount   int
	HasTests    bool
	Runtime     string // e.g. "Node 22", "Python 3.10"
	ConfigFiles []string
}

// Detect scans dir and returns a fully-populated Info.
func Detect(dir string) Info {
	if dir == "" {
		dir, _ = os.Getwd()
	}

	info := Info{
		RootDir: dir,
		Name:    filepath.Base(dir),
	}

	info.Language, info.Framework, info.PackageMgr = detectStack(dir)
	info.Runtime = detectRuntime(info.Language)
	info.GitBranch, info.GitDirty = detectGit(dir)
	info.FileCount = countSourceFiles(dir, info.Language)
	info.HasTests = hasTestDir(dir)
	info.ConfigFiles = detectConfigFiles(dir)

	return info
}

// Summary returns a compact one-line summary e.g. "React · TypeScript · npm · git:main"
func (i Info) Summary() string {
	parts := []string{}
	if i.Framework != "" {
		parts = append(parts, i.Framework)
	} else if i.Language != "" {
		parts = append(parts, i.Language)
	}
	if i.PackageMgr != "" {
		parts = append(parts, i.PackageMgr)
	}
	if i.GitBranch != "" {
		dirty := ""
		if i.GitDirty {
			dirty = "*"
		}
		parts = append(parts, fmt.Sprintf("git:%s%s", i.GitBranch, dirty))
	}
	if i.Runtime != "" {
		parts = append(parts, i.Runtime)
	}
	return strings.Join(parts, "  ·  ")
}

// ─── Internal detectors ───────────────────────────────────────────────────────

func detectStack(dir string) (lang, framework, pkgMgr string) {
	files := listDir(dir)

	// Go
	if has(files, "go.mod") {
		lang = "Go"
		if has(files, "main.go") {
			framework = "Go Binary"
		}
		pkgMgr = "go"
		return
	}

	// Rust
	if has(files, "Cargo.toml") {
		lang = "Rust"
		pkgMgr = "cargo"
		return
	}

	// Python
	if has(files, "pyproject.toml") || has(files, "setup.py") || has(files, "requirements.txt") {
		lang = "Python"
		if has(files, "pyproject.toml") {
			pkgMgr = "uv / pip"
		} else {
			pkgMgr = "pip"
		}
		if has(files, "manage.py") {
			framework = "Django"
		} else if hasContentMatch(dir, "requirements.txt", "flask") {
			framework = "Flask"
		} else if hasContentMatch(dir, "requirements.txt", "fastapi") {
			framework = "FastAPI"
		}
		return
	}

	// Node / JS / TS
	if has(files, "package.json") {
		lang = "TypeScript"
		if has(files, "yarn.lock") {
			pkgMgr = "yarn"
		} else if has(files, "pnpm-lock.yaml") {
			pkgMgr = "pnpm"
		} else {
			pkgMgr = "npm"
		}
		// Detect framework from package.json content
		content := readFile(filepath.Join(dir, "package.json"))
		switch {
		case strings.Contains(content, "\"next\""):
			framework = "Next.js"
		case strings.Contains(content, "\"vite\""):
			if strings.Contains(content, "\"react\"") {
				framework = "React + Vite"
			} else if strings.Contains(content, "\"vue\"") {
				framework = "Vue + Vite"
			} else {
				framework = "Vite"
			}
		case strings.Contains(content, "\"react\""):
			framework = "React"
		case strings.Contains(content, "\"vue\""):
			framework = "Vue"
		case strings.Contains(content, "\"svelte\""):
			framework = "Svelte"
		case strings.Contains(content, "\"express\""):
			framework = "Express"
		case strings.Contains(content, "\"fastify\""):
			framework = "Fastify"
		case strings.Contains(content, "\"nestjs\"") || strings.Contains(content, "\"@nestjs"):
			framework = "NestJS"
		}
		return
	}

	// Java / Kotlin / Spring
	if has(files, "pom.xml") {
		lang = "Java"
		framework = "Spring Boot"
		pkgMgr = "maven"
		return
	}
	if has(files, "build.gradle") || has(files, "build.gradle.kts") {
		lang = "Kotlin"
		framework = "Spring Boot"
		pkgMgr = "gradle"
		return
	}

	lang = "Unknown"
	return
}

func detectRuntime(lang string) string {
	switch lang {
	case "TypeScript", "JavaScript":
		out, err := exec.Command("node", "--version").Output()
		if err == nil {
			return "Node " + strings.TrimPrefix(strings.TrimSpace(string(out)), "v")
		}
	case "Python":
		out, err := exec.Command("python3", "--version").Output()
		if err == nil {
			return strings.TrimSpace(string(out))
		}
	case "Go":
		out, err := exec.Command("go", "version").Output()
		if err == nil {
			parts := strings.Fields(string(out))
			if len(parts) >= 3 {
				return parts[2]
			}
		}
	case "Rust":
		out, err := exec.Command("rustc", "--version").Output()
		if err == nil {
			parts := strings.Fields(string(out))
			if len(parts) >= 2 {
				return "Rust " + parts[1]
			}
		}
	}
	return ""
}

func detectGit(dir string) (branch string, dirty bool) {
	cmd := exec.Command("git", "-C", dir, "rev-parse", "--abbrev-ref", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return "", false
	}
	branch = strings.TrimSpace(string(out))

	statusCmd := exec.Command("git", "-C", dir, "status", "--porcelain")
	statusOut, err := statusCmd.Output()
	if err == nil {
		dirty = len(strings.TrimSpace(string(statusOut))) > 0
	}
	return
}

func countSourceFiles(dir, lang string) int {
	ext := map[string][]string{
		"Go":         {".go"},
		"TypeScript": {".ts", ".tsx", ".js", ".jsx"},
		"Python":     {".py"},
		"Rust":       {".rs"},
		"Java":       {".java"},
		"Kotlin":     {".kt", ".kts"},
	}
	exts, ok := ext[lang]
	if !ok {
		exts = []string{".go", ".ts", ".py", ".js", ".rs", ".java"}
	}
	count := 0
	_ = filepath.WalkDir(dir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			name := d.Name()
			if name == "node_modules" || name == ".git" || name == ".venv" ||
				name == "vendor" || name == "target" || name == "dist" || name == "build" {
				return filepath.SkipDir
			}
		}
		for _, e := range exts {
			if strings.HasSuffix(path, e) {
				count++
				break
			}
		}
		return nil
	})
	return count
}

func hasTestDir(dir string) bool {
	for _, d := range []string{"tests", "test", "__tests__", "spec"} {
		if _, err := os.Stat(filepath.Join(dir, d)); err == nil {
			return true
		}
	}
	return false
}

func detectConfigFiles(dir string) []string {
	candidates := []string{
		".env", ".env.local", "docker-compose.yml", "Dockerfile",
		".eslintrc", ".prettierrc", "tsconfig.json", "vite.config.ts",
		"tailwind.config.js", ".github",
	}
	var found []string
	for _, c := range candidates {
		if _, err := os.Stat(filepath.Join(dir, c)); err == nil {
			found = append(found, c)
		}
	}
	return found
}

// ─── Utils ────────────────────────────────────────────────────────────────────

func listDir(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	names := make([]string, 0, len(entries))
	for _, e := range entries {
		names = append(names, e.Name())
	}
	return names
}

func has(files []string, name string) bool {
	for _, f := range files {
		if f == name {
			return true
		}
	}
	return false
}

func readFile(path string) string {
	b, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	return string(b)
}

func hasContentMatch(dir, filename, keyword string) bool {
	content := readFile(filepath.Join(dir, filename))
	return strings.Contains(strings.ToLower(content), keyword)
}
