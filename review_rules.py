"""
Static analysis rules engine for the AI Code Review Agent.

Each rule returns a list of Issue dicts when triggered.
Rules are organized by category: security, bugs, style, performance, best_practices.
"""

import ast
import re
import textwrap
from typing import List, Dict, Any

Issue = Dict[str, Any]


# ---------------------------------------------------------------------------
# Security rules
# ---------------------------------------------------------------------------

def check_hardcoded_secrets(source: str, filename: str) -> List[Issue]:
    """Detect hardcoded passwords, API keys, tokens, and secrets."""
    issues: List[Issue] = []
    secret_patterns = [
        (r"""(?:password|passwd|pwd)\s*=\s*['"][^'"]{4,}['"]""", "hardcoded password"),
        (r"""(?:api_key|apikey|api_secret)\s*=\s*['"][^'"]{8,}['"]""", "hardcoded API key"),
        (r"""(?:secret|token|auth)\s*=\s*['"][^'"]{8,}['"]""", "hardcoded secret/token"),
        (r"""(?:AWS_ACCESS_KEY|aws_secret)\s*=\s*['"][^'"]{8,}['"]""", "hardcoded AWS credential"),
        (r"""['"](?:sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16})['"]""", "embedded cloud credential"),
    ]
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern, label in secret_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Exclude lines that read from env / config
                if "os.environ" in line or "getenv" in line or "config" in line.lower():
                    continue
                issues.append({
                    "file": filename,
                    "line": lineno,
                    "severity": "CRITICAL",
                    "category": "security",
                    "rule": "hardcoded-secret",
                    "message": f"Possible {label} found. Use environment variables instead.",
                })
    return issues


def check_sql_injection(source: str, filename: str) -> List[Issue]:
    """Detect string-formatted SQL queries (potential SQL injection)."""
    issues: List[Issue] = []
    sql_keywords = r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b"
    for lineno, line in enumerate(source.splitlines(), 1):
        if re.search(sql_keywords, line, re.IGNORECASE):
            if re.search(r"(?:f['\"]|\.format\(|%\s*[(\"])", line):
                issues.append({
                    "file": filename,
                    "line": lineno,
                    "severity": "CRITICAL",
                    "category": "security",
                    "rule": "sql-injection",
                    "message": "Potential SQL injection via string formatting. Use parameterized queries.",
                })
    return issues


def check_command_injection(source: str, filename: str) -> List[Issue]:
    """Detect os.system / subprocess with shell=True using user input."""
    issues: List[Issue] = []
    patterns = [
        (r"os\.system\(", "os.system() call — use subprocess with shell=False"),
        (r"subprocess\.(?:call|run|Popen)\(.*shell\s*=\s*True", "subprocess with shell=True"),
    ]
    for lineno, line in enumerate(source.splitlines(), 1):
        for pat, msg in patterns:
            if re.search(pat, line):
                issues.append({
                    "file": filename,
                    "line": lineno,
                    "severity": "HIGH",
                    "category": "security",
                    "rule": "command-injection",
                    "message": msg,
                })
    return issues


def check_eval_exec(source: str, filename: str) -> List[Issue]:
    """Flag usage of eval() and exec()."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"\beval\s*\(", line) or re.search(r"\bexec\s*\(", line):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "HIGH",
                "category": "security",
                "rule": "eval-exec",
                "message": "Use of eval()/exec() is dangerous. Avoid or use ast.literal_eval().",
            })
    return issues


def check_insecure_deserialization(source: str, filename: str) -> List[Issue]:
    """Flag pickle.loads / yaml.load without safe loader."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if "pickle.loads" in line or "pickle.load(" in line:
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "HIGH",
                "category": "security",
                "rule": "insecure-deserialization",
                "message": "pickle.load(s) can execute arbitrary code. Avoid on untrusted data.",
            })
        if re.search(r"yaml\.load\(", line) and "Loader=" not in line:
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "HIGH",
                "category": "security",
                "rule": "insecure-yaml",
                "message": "yaml.load() without Loader is unsafe. Use yaml.safe_load().",
            })
    return issues


# ---------------------------------------------------------------------------
# Bug / correctness rules
# ---------------------------------------------------------------------------

def check_bare_except(source: str, filename: str) -> List[Issue]:
    """Detect bare except clauses."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped == "except:" or re.match(r"^except\s*:\s*$", stripped):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "MEDIUM",
                "category": "bug",
                "rule": "bare-except",
                "message": "Bare except catches all exceptions including KeyboardInterrupt. Specify exception type.",
            })
    return issues


def check_mutable_default_args(source: str, filename: str) -> List[Issue]:
    """Detect mutable default arguments in function definitions."""
    issues: List[Issue] = []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is None:
                    continue
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append({
                        "file": filename,
                        "line": node.lineno,
                        "severity": "MEDIUM",
                        "category": "bug",
                        "rule": "mutable-default-arg",
                        "message": f"Mutable default argument in '{node.name}()'. Use None and create inside the function.",
                    })
    return issues


def check_unused_variables(source: str, filename: str) -> List[Issue]:
    """Detect obviously unused local variables (simple heuristic)."""
    issues: List[Issue] = []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assigned = {}
            used = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and not target.id.startswith("_"):
                            assigned[target.id] = child.lineno
                elif isinstance(child, ast.Name) and not isinstance(child.ctx, ast.Store):
                    used.add(child.id)
            for var, lineno in assigned.items():
                if var not in used and var != "self":
                    issues.append({
                        "file": filename,
                        "line": lineno,
                        "severity": "LOW",
                        "category": "bug",
                        "rule": "unused-variable",
                        "message": f"Variable '{var}' is assigned but never used in '{node.name}()'.",
                    })
    return issues


def check_global_usage(source: str, filename: str) -> List[Issue]:
    """Flag usage of the global keyword."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if re.match(r"^global\s+\w+", stripped):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "MEDIUM",
                "category": "bug",
                "rule": "global-variable",
                "message": "Use of 'global' makes state hard to track. Consider using a class or passing arguments.",
            })
    return issues


# ---------------------------------------------------------------------------
# Style rules
# ---------------------------------------------------------------------------

def check_line_length(source: str, filename: str, max_len: int = 120) -> List[Issue]:
    """Flag lines exceeding the maximum length."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if len(line) > max_len:
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "LOW",
                "category": "style",
                "rule": "line-too-long",
                "message": f"Line is {len(line)} chars (max {max_len}).",
            })
    return issues


def check_missing_docstrings(source: str, filename: str) -> List[Issue]:
    """Flag public functions/classes missing docstrings."""
    issues: List[Issue] = []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            docstring = ast.get_docstring(node)
            if not docstring:
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                issues.append({
                    "file": filename,
                    "line": node.lineno,
                    "severity": "LOW",
                    "category": "style",
                    "rule": "missing-docstring",
                    "message": f"Public {kind} '{node.name}' is missing a docstring.",
                })
    return issues


# ---------------------------------------------------------------------------
# Performance rules
# ---------------------------------------------------------------------------

def check_loop_inefficiencies(source: str, filename: str) -> List[Issue]:
    """Detect common loop anti-patterns."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if re.search(r"for\s+\w+\s+in\s+range\(len\(", line):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "LOW",
                "category": "performance",
                "rule": "range-len",
                "message": "Use 'for item in iterable' or 'enumerate()' instead of 'range(len())'.",
            })
        if re.search(r"\+\s*=\s*\[", line) or re.search(r"=\s*\w+\s*\+\s*\[", line):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "LOW",
                "category": "performance",
                "rule": "list-concat-in-loop",
                "message": "Repeated list concatenation is O(n^2). Use list.append() or list.extend().",
            })
    return issues


def check_star_imports(source: str, filename: str) -> List[Issue]:
    """Flag wildcard imports."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if re.match(r"^\s*from\s+\S+\s+import\s+\*", line):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "MEDIUM",
                "category": "best_practices",
                "rule": "star-import",
                "message": "Wildcard import pollutes namespace. Import specific names.",
            })
    return issues


# ---------------------------------------------------------------------------
# Best practices rules
# ---------------------------------------------------------------------------

def check_exception_handling(source: str, filename: str) -> List[Issue]:
    """Detect overly broad exception handling (except Exception)."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if re.match(r"^except\s+Exception\s*:", stripped):
            # Check if the next non-empty line is just pass or continue
            lines = source.splitlines()
            if lineno < len(lines):
                next_line = lines[lineno].strip()
                if next_line in ("pass", "continue", "..."):
                    issues.append({
                        "file": filename,
                        "line": lineno,
                        "severity": "MEDIUM",
                        "category": "best_practices",
                        "rule": "swallowed-exception",
                        "message": "Exception is caught and silently ignored. Log or handle it.",
                    })
    return issues


def check_todo_fixme(source: str, filename: str) -> List[Issue]:
    """Flag TODO and FIXME comments."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        if re.search(r"#\s*(?:TODO|FIXME|HACK|XXX)\b", line, re.IGNORECASE):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "INFO",
                "category": "best_practices",
                "rule": "todo-comment",
                "message": "Unresolved TODO/FIXME comment.",
            })
    return issues


def check_print_statements(source: str, filename: str) -> List[Issue]:
    """Flag print() in production code (should use logging)."""
    issues: List[Issue] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"\bprint\s*\(", stripped):
            issues.append({
                "file": filename,
                "line": lineno,
                "severity": "LOW",
                "category": "best_practices",
                "rule": "print-statement",
                "message": "Consider using the logging module instead of print().",
            })
    return issues


def check_type_hints(source: str, filename: str) -> List[Issue]:
    """Flag functions without type hints."""
    issues: List[Issue] = []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and node.name != "__init__":
                continue
            if node.returns is None:
                issues.append({
                    "file": filename,
                    "line": node.lineno,
                    "severity": "LOW",
                    "category": "best_practices",
                    "rule": "missing-return-type",
                    "message": f"Function '{node.name}' is missing a return type annotation.",
                })
    return issues


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_RULES = [
    # Security
    check_hardcoded_secrets,
    check_sql_injection,
    check_command_injection,
    check_eval_exec,
    check_insecure_deserialization,
    # Bug / correctness
    check_bare_except,
    check_mutable_default_args,
    check_unused_variables,
    check_global_usage,
    # Style
    check_line_length,
    check_missing_docstrings,
    # Performance
    check_loop_inefficiencies,
    check_star_imports,
    # Best practices
    check_exception_handling,
    check_todo_fixme,
    check_print_statements,
    check_type_hints,
]


def run_all_rules(source: str, filename: str) -> List[Issue]:
    """Execute every registered rule against *source* and return all issues."""
    issues: List[Issue] = []
    for rule_fn in ALL_RULES:
        try:
            issues.extend(rule_fn(source, filename))
        except Exception:
            pass  # never let a single rule crash the whole review
    return issues
