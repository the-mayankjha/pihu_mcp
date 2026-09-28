package render

import (
	"strings"
	"testing"
)

func TestMarkdownRendering(t *testing.T) {
	r := New(80)
	sample := `I have created and executed the Python pattern program at test/python.py.

### 📄 Code (test/python.py)
` + "```python\n" + `def print_diamond_pattern(n):
    for i in range(n):
        print(" " * (n - i - 1) + "* " * (i + 1))
` + "```\n\n" + `### 🖥 Output
` + "```output\n" + `=== Diamond Pattern ===
  *
 * *
* * *
` + "```"

	rendered := r.Markdown(sample)
	if !strings.Contains(rendered, "Python") {
		t.Errorf("Expected Python label in rendered output, got: %s", rendered)
	}
	if !strings.Contains(rendered, "Output") {
		t.Errorf("Expected Output label in rendered output, got: %s", rendered)
	}
	if !strings.Contains(rendered, "1 │") {
		t.Errorf("Expected line numbers in rendered output, got: %s", rendered)
	}
}
