"""
AI Code Detection Bot

Analyzes PR diffs to detect patterns commonly associated with AI-generated code.
Uses heuristic analysis across multiple signals to produce a confidence score.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns & Signals
# ---------------------------------------------------------------------------

# Comment patterns strongly associated with AI-generated code
AI_COMMENT_PATTERNS = [
    # Obvious AI markers
    r"(?i)generated\s+by\s+(ai|chatgpt|copilot|claude|gemini|gpt|llm)",
    r"(?i)auto[\-\s]?generated",
    r"(?i)ai[\-\s]?generated",
    # Over-explained comments typical of AI
    r"(?i)#\s*this\s+(function|method|class|variable|loop|block)\s+(is|will|does|handles|takes|returns|creates|initializes|performs)",
    r"(?i)//\s*this\s+(function|method|class|variable|loop|block)\s+(is|will|does|handles|takes|returns|creates|initializes|performs)",
    r"(?i)#\s*here\s+we\s+(are|define|create|initialize|set|handle|process)",
    r"(?i)//\s*here\s+we\s+(are|define|create|initialize|set|handle|process)",
    # Placeholder / TODO patterns AI commonly leaves
    r"(?i)#\s*todo:\s*implement",
    r"(?i)//\s*todo:\s*implement",
    r"(?i)#\s*add\s+your\s+(code|logic|implementation)\s+here",
    r"(?i)//\s*add\s+your\s+(code|logic|implementation)\s+here",
    r"(?i)pass\s*#\s*placeholder",
    # Docstring patterns
    r'(?i)""".*\bArgs\s*:',
    r'(?i)""".*\bReturns\s*:',
    r'(?i)""".*\bRaises\s*:',
    r'(?i)""".*\bExample\s*:',
]

# Structural patterns AI tends to produce
AI_STRUCTURE_PATTERNS = [
    # Overly defensive error handling
    r"except\s+Exception\s+as\s+e\s*:",
    r"catch\s*\(\s*error\s*\)\s*\{",
    r"catch\s*\(\s*err\s*\)\s*\{",
    # Verbose logging of every step
    r'(?i)(logger|logging|console)\.(info|log|debug)\s*\(\s*f?["\'].*(?:starting|beginning|initiating|processing|completed|finished|done)',
    # Type hints on every parameter (unusual for human quick code)
    r"def\s+\w+\s*\([^)]*:\s*\w+[^)]*:\s*\w+[^)]*:\s*\w+",
    # AI-style variable naming (overly descriptive)
    r"\b(result_list|data_dict|output_string|input_value|temp_variable|is_valid|should_continue)\b",
    # AI-favored import grouping with blank lines between groups
    r"^import\s+\w+\n\nimport\s+\w+",
]

# Phrases AI commonly uses in code or comments
AI_PHRASES = [
    "note that", "it's worth noting", "as mentioned above",
    "for simplicity", "for clarity", "for readability",
    "robust", "comprehensive", "edge case", "gracefully",
    "straightforward", "as expected", "as shown above",
    "the following", "as follows", "in this case",
    "ensure that", "make sure", "don't forget to",
    "feel free to", "you can also", "alternatively",
    "leverage", "utilize", "facilitate",
]

# File extensions to analyze
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".yml", ".yaml",
}


@dataclass
class FileAnalysis:
    """Analysis result for a single file."""
    filename: str
    total_lines_added: int = 0
    ai_signals: list = field(default_factory=list)
    confidence: float = 0.0

    @property
    def verdict(self) -> str:
        if self.confidence >= 0.7:
            return "Likely AI-generated"
        elif self.confidence >= 0.4:
            return "Possibly AI-generated"
        else:
            return "Likely human-written"


@dataclass
class DetectionReport:
    """Overall detection report for the PR."""
    file_analyses: list = field(default_factory=list)

    @property
    def overall_confidence(self) -> float:
        if not self.file_analyses:
            return 0.0
        weighted = sum(a.confidence * a.total_lines_added for a in self.file_analyses)
        total_lines = sum(a.total_lines_added for a in self.file_analyses)
        return weighted / total_lines if total_lines > 0 else 0.0

    @property
    def overall_verdict(self) -> str:
        c = self.overall_confidence
        if c >= 0.7:
            return "Likely AI-generated"
        elif c >= 0.4:
            return "Possibly AI-generated"
        else:
            return "Likely human-written"


# ---------------------------------------------------------------------------
# Diff Parsing
# ---------------------------------------------------------------------------

def parse_diff(diff_text: str) -> dict[str, list[str]]:
    """Parse a unified diff and return {filename: [added_lines]}."""
    files: dict[str, list[str]] = {}
    current_file = None

    for line in diff_text.splitlines():
        # Detect file header
        if line.startswith("+++ b/"):
            current_file = line[6:]
            if current_file not in files:
                files[current_file] = []
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file:
                files[current_file].append(line[1:])  # strip leading +

    return files


# ---------------------------------------------------------------------------
# Analysis Engine
# ---------------------------------------------------------------------------

def analyze_file(filename: str, added_lines: list[str]) -> FileAnalysis:
    """Analyze added lines of a single file for AI-generation signals."""
    analysis = FileAnalysis(filename=filename, total_lines_added=len(added_lines))

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS or len(added_lines) < 3:
        return analysis

    content = "\n".join(added_lines)
    content_lower = content.lower()
    signals = []

    # 1. Check AI comment patterns
    comment_hits = 0
    for pattern in AI_COMMENT_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            comment_hits += len(matches)
            signals.append(f"AI comment pattern: `{pattern}` ({len(matches)} hits)")

    # 2. Check structural patterns
    structure_hits = 0
    for pattern in AI_STRUCTURE_PATTERNS:
        matches = re.findall(pattern, content, re.MULTILINE)
        if matches:
            structure_hits += len(matches)
            signals.append(f"AI structure pattern: ({len(matches)} hits)")

    # 3. Check AI phrases in comments and strings
    phrase_hits = 0
    for phrase in AI_PHRASES:
        count = content_lower.count(phrase)
        if count > 0:
            phrase_hits += count
            signals.append(f"AI phrase: \"{phrase}\" ({count} hits)")

    # 4. Comment density analysis (AI tends to over-comment)
    comment_lines = sum(
        1 for line in added_lines
        if line.strip().startswith(("#", "//", "/*", "*", "'''", '"""'))
    )
    code_lines = len(added_lines) - comment_lines
    comment_ratio = comment_lines / len(added_lines) if added_lines else 0
    if comment_ratio > 0.35 and len(added_lines) > 10:
        signals.append(f"High comment ratio: {comment_ratio:.0%} ({comment_lines}/{len(added_lines)} lines)")

    # 5. Uniformity of line length (AI tends to produce consistent line lengths)
    non_empty = [len(line) for line in added_lines if line.strip()]
    if len(non_empty) > 10:
        avg_len = sum(non_empty) / len(non_empty)
        variance = sum((l - avg_len) ** 2 for l in non_empty) / len(non_empty)
        std_dev = variance ** 0.5
        if std_dev < 12 and avg_len > 20:
            signals.append(f"Uniform line lengths (std_dev={std_dev:.1f}, avg={avg_len:.1f})")

    # 6. Consistent naming convention (AI almost never mixes styles)
    snake_count = len(re.findall(r"\b[a-z]+_[a-z]+\b", content))
    camel_count = len(re.findall(r"\b[a-z]+[A-Z][a-z]+\b", content))
    if snake_count > 5 and camel_count == 0:
        signals.append("Perfectly consistent snake_case naming")
    elif camel_count > 5 and snake_count == 0:
        signals.append("Perfectly consistent camelCase naming")

    # 7. Excessive type hints / annotations
    type_hint_lines = sum(1 for line in added_lines if re.search(r":\s*(str|int|float|bool|list|dict|Optional|Union|Any)\b", line))
    if type_hint_lines > 5 and type_hint_lines / max(code_lines, 1) > 0.3:
        signals.append(f"Heavy type annotation usage: {type_hint_lines} lines")

    # 8. Large uniform blocks (AI writes long uninterrupted blocks)
    consecutive_code = 0
    max_consecutive = 0
    for line in added_lines:
        if line.strip() and not line.strip().startswith(("#", "//", "/*", "*")):
            consecutive_code += 1
            max_consecutive = max(max_consecutive, consecutive_code)
        else:
            consecutive_code = 0
    if max_consecutive > 40:
        signals.append(f"Large uninterrupted code block: {max_consecutive} lines")

    # --- Compute confidence score ---
    score = 0.0
    score += min(comment_hits * 0.15, 0.45)    # AI comments: up to 0.45
    score += min(structure_hits * 0.08, 0.24)   # Structure patterns: up to 0.24
    score += min(phrase_hits * 0.06, 0.18)      # AI phrases: up to 0.18
    if comment_ratio > 0.35 and len(added_lines) > 10:
        score += 0.10
    if non_empty and len(non_empty) > 10:
        if std_dev < 12 and avg_len > 20:
            score += 0.08
    if max_consecutive > 40:
        score += 0.05

    analysis.confidence = min(score, 1.0)
    analysis.ai_signals = signals
    return analysis


def run_detection(diff_path: str) -> DetectionReport:
    """Run AI detection on a diff file."""
    diff_text = Path(diff_path).read_text(encoding="utf-8", errors="replace")
    files = parse_diff(diff_text)
    report = DetectionReport()

    for filename, added_lines in files.items():
        analysis = analyze_file(filename, added_lines)
        if analysis.total_lines_added > 0:
            report.file_analyses.append(analysis)

    return report


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def confidence_bar(confidence: float) -> str:
    """Generate a visual confidence bar."""
    filled = round(confidence * 10)
    empty = 10 - filled
    return f"[{'█' * filled}{'░' * empty}] {confidence:.0%}"


def verdict_emoji(verdict: str) -> str:
    if "Likely AI" in verdict:
        return "🤖"
    elif "Possibly" in verdict:
        return "🤔"
    else:
        return "✅"


def generate_report_markdown(report: DetectionReport) -> str:
    """Generate the markdown report to post as a PR comment."""
    v = report.overall_verdict
    emoji = verdict_emoji(v)

    lines = [
        f"## {emoji} AI Code Detection Report",
        "",
        f"**Overall Verdict:** {v}",
        f"**Confidence:** {confidence_bar(report.overall_confidence)}",
        "",
    ]

    # Summary table
    flagged = [a for a in report.file_analyses if a.confidence >= 0.4]
    clean = [a for a in report.file_analyses if a.confidence < 0.4]

    if flagged:
        lines.append("### Flagged Files")
        lines.append("")
        lines.append("| File | Lines Added | Confidence | Verdict |")
        lines.append("|------|------------|------------|---------|")
        for a in sorted(flagged, key=lambda x: -x.confidence):
            lines.append(
                f"| `{a.filename}` | {a.total_lines_added} | {confidence_bar(a.confidence)} | {verdict_emoji(a.verdict)} {a.verdict} |"
            )
        lines.append("")

    if clean:
        lines.append(f"<details><summary>✅ {len(clean)} file(s) appear human-written</summary>")
        lines.append("")
        for a in clean:
            lines.append(f"- `{a.filename}` ({a.total_lines_added} lines added)")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    # Detailed signals for flagged files
    if flagged:
        lines.append("### Detected Signals")
        lines.append("")
        for a in sorted(flagged, key=lambda x: -x.confidence):
            lines.append(f"<details><summary><code>{a.filename}</code> — {a.confidence:.0%} confidence</summary>")
            lines.append("")
            for signal in a.ai_signals:
                lines.append(f"- {signal}")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    lines.append("---")
    lines.append(
        "*This is a heuristic analysis and may produce false positives. "
        "AI-generated code is not inherently bad — this report is informational only.*"
    )
    lines.append("")
    lines.append(f"📊 Analyzed **{len(report.file_analyses)}** file(s), "
                 f"**{sum(a.total_lines_added for a in report.file_analyses)}** lines added")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python detect.py <diff_file>")
        sys.exit(1)

    diff_path = sys.argv[1]
    if not Path(diff_path).exists():
        print(f"Diff file not found: {diff_path}")
        # Write a minimal report
        with open("/tmp/ai_detection_report.md", "w") as f:
            f.write("## AI Code Detection Report\n\nNo diff found to analyze.\n")
        sys.exit(0)

    report = run_detection(diff_path)
    markdown = generate_report_markdown(report)

    # Write report for the workflow to pick up
    with open("/tmp/ai_detection_report.md", "w") as f:
        f.write(markdown)

    print(markdown)

    # Set exit code based on verdict (non-zero = flagged, for optional CI gating)
    if report.overall_confidence >= 0.7:
        sys.exit(0)  # Still exit 0 so the workflow posts the comment
    sys.exit(0)


if __name__ == "__main__":
    main()
