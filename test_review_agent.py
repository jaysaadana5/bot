#!/usr/bin/env python3
"""
Comprehensive test suite for the AI Code Review Agent.

Tests are organized by rule category.  Each test provides a code snippet that
**must** trigger (true positive) or **must not** trigger (true negative) a
specific rule.  The overall accuracy target is >98%.

Run:
    python -m pytest test_review_agent.py -v
    python test_review_agent.py          # standalone runner
"""

import json
import sys
import textwrap
from typing import List, Set

from review_rules import (
    ALL_RULES,
    run_all_rules,
    check_hardcoded_secrets,
    check_sql_injection,
    check_command_injection,
    check_eval_exec,
    check_insecure_deserialization,
    check_bare_except,
    check_mutable_default_args,
    check_unused_variables,
    check_global_usage,
    check_line_length,
    check_missing_docstrings,
    check_loop_inefficiencies,
    check_star_imports,
    check_exception_handling,
    check_todo_fixme,
    check_print_statements,
    check_type_hints,
)
from code_review_agent import CodeReviewAgent


# ===================================================================
# Test infrastructure
# ===================================================================
class TestResult:
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail


results: List[TestResult] = []


def check(name: str, condition: bool, detail: str = ""):
    results.append(TestResult(name, condition, detail))


def has_rule(issues, rule_id: str) -> bool:
    return any(i["rule"] == rule_id for i in issues)


def has_severity(issues, severity: str) -> bool:
    return any(i["severity"] == severity for i in issues)


def has_category(issues, category: str) -> bool:
    return any(i["category"] == category for i in issues)


# ===================================================================
# SECURITY TESTS
# ===================================================================

def test_hardcoded_password_detected():
    code = 'password = "SuperSecret123!"\n'
    issues = check_hardcoded_secrets(code, "test.py")
    check("SEC-001: detect hardcoded password", len(issues) >= 1)
    if issues:
        check("SEC-001: severity is CRITICAL", issues[0]["severity"] == "CRITICAL")


def test_hardcoded_api_key_detected():
    code = 'api_key = "sk-abc123def456ghi789"\n'
    issues = check_hardcoded_secrets(code, "test.py")
    check("SEC-002: detect hardcoded API key", len(issues) >= 1)


def test_env_var_not_flagged():
    code = 'password = os.environ.get("DB_PASSWORD")\n'
    issues = check_hardcoded_secrets(code, "test.py")
    check("SEC-003: env var usage NOT flagged", len(issues) == 0)


def test_sql_injection_fstring():
    code = 'query = f"SELECT * FROM users WHERE id = {user_id}"\n'
    issues = check_sql_injection(code, "test.py")
    check("SEC-004: detect SQL injection (f-string)", len(issues) >= 1)


def test_sql_injection_format():
    code = 'query = "SELECT * FROM users WHERE id = {}".format(user_id)\n'
    issues = check_sql_injection(code, "test.py")
    check("SEC-005: detect SQL injection (.format)", len(issues) >= 1)


def test_safe_sql_not_flagged():
    code = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))\n'
    issues = check_sql_injection(code, "test.py")
    check("SEC-006: parameterized SQL NOT flagged", len(issues) == 0)


def test_os_system_detected():
    code = 'os.system("rm -rf " + user_input)\n'
    issues = check_command_injection(code, "test.py")
    check("SEC-007: detect os.system()", len(issues) >= 1)


def test_subprocess_shell_true():
    code = 'subprocess.call(cmd, shell=True)\n'
    issues = check_command_injection(code, "test.py")
    check("SEC-008: detect subprocess shell=True", len(issues) >= 1)


def test_subprocess_shell_false_ok():
    code = 'subprocess.run(["ls", "-la"])\n'
    issues = check_command_injection(code, "test.py")
    check("SEC-009: subprocess without shell NOT flagged", len(issues) == 0)


def test_eval_detected():
    code = 'result = eval(user_input)\n'
    issues = check_eval_exec(code, "test.py")
    check("SEC-010: detect eval()", len(issues) >= 1)


def test_exec_detected():
    code = 'exec(code_string)\n'
    issues = check_eval_exec(code, "test.py")
    check("SEC-011: detect exec()", len(issues) >= 1)


def test_pickle_loads_detected():
    code = 'data = pickle.loads(untrusted_bytes)\n'
    issues = check_insecure_deserialization(code, "test.py")
    check("SEC-012: detect pickle.loads()", len(issues) >= 1)


def test_yaml_load_unsafe():
    code = 'data = yaml.load(content)\n'
    issues = check_insecure_deserialization(code, "test.py")
    check("SEC-013: detect yaml.load() without Loader", len(issues) >= 1)


def test_yaml_safe_load_ok():
    code = 'data = yaml.safe_load(content)\n'
    issues = check_insecure_deserialization(code, "test.py")
    check("SEC-014: yaml.safe_load() NOT flagged", len(issues) == 0)


def test_yaml_load_with_loader_ok():
    code = 'data = yaml.load(content, Loader=yaml.SafeLoader)\n'
    issues = check_insecure_deserialization(code, "test.py")
    check("SEC-015: yaml.load() with Loader NOT flagged", len(issues) == 0)


def test_aws_credential_detected():
    code = 'key = "AKIAIOSFODNN7EXAMPLE"\n'
    issues = check_hardcoded_secrets(code, "test.py")
    check("SEC-016: detect embedded AWS key", len(issues) >= 1)


# ===================================================================
# BUG / CORRECTNESS TESTS
# ===================================================================

def test_bare_except_detected():
    code = textwrap.dedent("""\
        try:
            do_something()
        except:
            pass
    """)
    issues = check_bare_except(code, "test.py")
    check("BUG-001: detect bare except", len(issues) >= 1)


def test_specific_except_ok():
    code = textwrap.dedent("""\
        try:
            do_something()
        except ValueError:
            pass
    """)
    issues = check_bare_except(code, "test.py")
    check("BUG-002: specific except NOT flagged", len(issues) == 0)


def test_mutable_default_list():
    code = textwrap.dedent("""\
        def foo(items=[]):
            items.append(1)
            return items
    """)
    issues = check_mutable_default_args(code, "test.py")
    check("BUG-003: mutable default (list) detected", len(issues) >= 1)


def test_mutable_default_dict():
    code = textwrap.dedent("""\
        def foo(config={}):
            return config
    """)
    issues = check_mutable_default_args(code, "test.py")
    check("BUG-004: mutable default (dict) detected", len(issues) >= 1)


def test_immutable_default_ok():
    code = textwrap.dedent("""\
        def foo(count=0, name="default"):
            return count, name
    """)
    issues = check_mutable_default_args(code, "test.py")
    check("BUG-005: immutable default NOT flagged", len(issues) == 0)


def test_none_default_ok():
    code = textwrap.dedent("""\
        def foo(items=None):
            if items is None:
                items = []
            return items
    """)
    issues = check_mutable_default_args(code, "test.py")
    check("BUG-006: None default NOT flagged", len(issues) == 0)


def test_unused_variable_detected():
    code = textwrap.dedent("""\
        def process():
            unused_var = 42
            return True
    """)
    issues = check_unused_variables(code, "test.py")
    check("BUG-007: unused variable detected", len(issues) >= 1)


def test_used_variable_ok():
    code = textwrap.dedent("""\
        def process():
            result = compute()
            return result
    """)
    issues = check_unused_variables(code, "test.py")
    check("BUG-008: used variable NOT flagged", len(issues) == 0)


def test_underscore_variable_ok():
    code = textwrap.dedent("""\
        def process():
            _ignored = compute()
            return True
    """)
    issues = check_unused_variables(code, "test.py")
    check("BUG-009: _underscore variable NOT flagged", len(issues) == 0)


def test_global_keyword_detected():
    code = textwrap.dedent("""\
        counter = 0
        def increment():
            global counter
            counter += 1
    """)
    issues = check_global_usage(code, "test.py")
    check("BUG-010: global keyword detected", len(issues) >= 1)


# ===================================================================
# STYLE TESTS
# ===================================================================

def test_long_line_detected():
    code = "x = " + "a" * 120 + "\n"
    issues = check_line_length(code, "test.py")
    check("STY-001: long line detected", len(issues) >= 1)


def test_normal_line_ok():
    code = "x = 42\n"
    issues = check_line_length(code, "test.py")
    check("STY-002: normal line NOT flagged", len(issues) == 0)


def test_missing_docstring_function():
    code = textwrap.dedent("""\
        def public_function():
            return 42
    """)
    issues = check_missing_docstrings(code, "test.py")
    check("STY-003: missing docstring detected (function)", len(issues) >= 1)


def test_docstring_present_ok():
    code = textwrap.dedent('''\
        def public_function():
            """This function does something."""
            return 42
    ''')
    issues = check_missing_docstrings(code, "test.py")
    check("STY-004: docstring present NOT flagged", len(issues) == 0)


def test_private_function_no_docstring_ok():
    code = textwrap.dedent("""\
        def _private_helper():
            return 42
    """)
    issues = check_missing_docstrings(code, "test.py")
    check("STY-005: private function missing docstring NOT flagged", len(issues) == 0)


def test_missing_docstring_class():
    code = textwrap.dedent("""\
        class MyClass:
            pass
    """)
    issues = check_missing_docstrings(code, "test.py")
    check("STY-006: missing docstring detected (class)", len(issues) >= 1)


# ===================================================================
# PERFORMANCE TESTS
# ===================================================================

def test_range_len_detected():
    code = "for i in range(len(items)):\n    print(items[i])\n"
    issues = check_loop_inefficiencies(code, "test.py")
    check("PERF-001: range(len()) detected", len(issues) >= 1)


def test_enumerate_ok():
    code = "for i, item in enumerate(items):\n    print(i, item)\n"
    issues = check_loop_inefficiencies(code, "test.py")
    check("PERF-002: enumerate() NOT flagged", len(issues) == 0)


def test_star_import_detected():
    code = "from os.path import *\n"
    issues = check_star_imports(code, "test.py")
    check("PERF-003: star import detected", len(issues) >= 1)


def test_specific_import_ok():
    code = "from os.path import join, exists\n"
    issues = check_star_imports(code, "test.py")
    check("PERF-004: specific import NOT flagged", len(issues) == 0)


# ===================================================================
# BEST PRACTICES TESTS
# ===================================================================

def test_swallowed_exception_detected():
    code = textwrap.dedent("""\
        try:
            risky()
        except Exception:
            pass
    """)
    issues = check_exception_handling(code, "test.py")
    check("BP-001: swallowed exception detected", len(issues) >= 1)


def test_handled_exception_ok():
    code = textwrap.dedent("""\
        try:
            risky()
        except Exception as e:
            logger.error(e)
    """)
    issues = check_exception_handling(code, "test.py")
    check("BP-002: handled exception NOT flagged", len(issues) == 0)


def test_todo_comment_detected():
    code = "# TODO: fix this later\n"
    issues = check_todo_fixme(code, "test.py")
    check("BP-003: TODO comment detected", len(issues) >= 1)


def test_fixme_comment_detected():
    code = "# FIXME: broken edge case\n"
    issues = check_todo_fixme(code, "test.py")
    check("BP-004: FIXME comment detected", len(issues) >= 1)


def test_normal_comment_ok():
    code = "# This is a normal comment\n"
    issues = check_todo_fixme(code, "test.py")
    check("BP-005: normal comment NOT flagged", len(issues) == 0)


def test_print_detected():
    code = 'print("debug output")\n'
    issues = check_print_statements(code, "test.py")
    check("BP-006: print() detected", len(issues) >= 1)


def test_commented_print_ok():
    code = '# print("debug output")\n'
    issues = check_print_statements(code, "test.py")
    check("BP-007: commented print NOT flagged", len(issues) == 0)


def test_missing_return_type_detected():
    code = textwrap.dedent("""\
        def compute(x):
            return x * 2
    """)
    issues = check_type_hints(code, "test.py")
    check("BP-008: missing return type detected", len(issues) >= 1)


def test_return_type_present_ok():
    code = textwrap.dedent("""\
        def compute(x) -> int:
            return x * 2
    """)
    issues = check_type_hints(code, "test.py")
    check("BP-009: return type present NOT flagged", len(issues) == 0)


# ===================================================================
# INTEGRATION TESTS
# ===================================================================

def test_run_all_rules_clean_code():
    """Clean code should produce only low-severity / info issues."""
    code = textwrap.dedent('''\
        """Module docstring."""
        import os


        def greet(name: str) -> str:
            """Return a greeting."""
            return f"Hello, {name}!"
    ''')
    issues = run_all_rules(code, "clean.py")
    critical_high = [i for i in issues if i["severity"] in ("CRITICAL", "HIGH")]
    check("INT-001: clean code has no CRITICAL/HIGH issues", len(critical_high) == 0)


def test_run_all_rules_vulnerable_code():
    """Vulnerable code must trigger multiple security findings."""
    code = textwrap.dedent("""\
        import os
        password = "hunter2"
        os.system("rm -rf " + user_input)
        result = eval(user_input)
        query = f"SELECT * FROM users WHERE id = {uid}"
    """)
    issues = run_all_rules(code, "vuln.py")
    security_issues = [i for i in issues if i["category"] == "security"]
    check("INT-002: vulnerable code has >= 3 security issues", len(security_issues) >= 3)


def test_run_all_rules_buggy_code():
    """Code with known bugs must be caught."""
    code = textwrap.dedent("""\
        def process(items=[]):
            try:
                do_work()
            except:
                pass
            global state
            unused = 42
            return items
    """)
    issues = run_all_rules(code, "buggy.py")
    bug_rules = {i["rule"] for i in issues}
    check("INT-003: mutable default caught", "mutable-default-arg" in bug_rules)
    check("INT-004: bare except caught", "bare-except" in bug_rules)
    check("INT-005: global caught", "global-variable" in bug_rules)


def test_agent_review_source_static_only():
    """CodeReviewAgent in static-only mode should work without API key."""
    agent = CodeReviewAgent(use_ai=False)
    code = textwrap.dedent("""\
        password = "secret123"
        eval(input())
    """)
    report = agent.review_source(code, "test_input.py")
    check("INT-006: agent returns file_review type", report["type"] == "file_review")
    check("INT-007: agent finds issues", report["total_issues"] > 0)
    check("INT-008: agent computes quality score", "quality_score" in report)
    check("INT-009: agent includes summary", "summary" in report)


def test_agent_quality_score_range():
    """Quality score should be between 0 and 100."""
    agent = CodeReviewAgent(use_ai=False)
    # Very bad code
    bad_code = 'password="xyzSecret99"\n' * 50
    report = agent.review_source(bad_code, "bad.py")
    score = report["quality_score"]
    check("INT-010: quality score >= 0", score >= 0)
    check("INT-011: quality score <= 100", score <= 100)

    # Clean code
    good_code = textwrap.dedent('''\
        """Clean module."""

        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b
    ''')
    report2 = agent.review_source(good_code, "good.py")
    check("INT-012: clean code scores higher", report2["quality_score"] > score)


def test_severity_filter():
    """Severity threshold should filter out lower-priority issues."""
    agent_all = CodeReviewAgent(use_ai=False, severity_threshold="INFO")
    agent_high = CodeReviewAgent(use_ai=False, severity_threshold="HIGH")

    code = textwrap.dedent("""\
        password = "secret"
        eval(input())
        x = 42
        print(x)
    """)
    report_all = agent_all.review_source(code, "test.py")
    report_high = agent_high.review_source(code, "test.py")
    check(
        "INT-013: HIGH filter returns fewer issues",
        report_high["total_issues"] <= report_all["total_issues"],
    )


def test_deduplication():
    """Same issue should not appear twice."""
    agent = CodeReviewAgent(use_ai=False)
    code = 'password = "abc12345"\n'
    report = agent.review_source(code, "test.py")
    rules = [i["rule"] for i in report["issues"]]
    # Count hardcoded-secret occurrences
    count = rules.count("hardcoded-secret")
    check("INT-014: no duplicate issues", count <= 1)


def test_diff_review():
    """Diff review should parse added lines and find issues."""
    agent = CodeReviewAgent(use_ai=False)
    diff = textwrap.dedent("""\
        diff --git a/app.py b/app.py
        --- a/app.py
        +++ b/app.py
        @@ -1,3 +1,5 @@
         import os
        +password = "letmein"
        +os.system("rm " + path)
         def main():
             pass
    """)
    report = agent.review_diff(diff)
    check("INT-015: diff review finds issues", report["total_issues"] > 0)
    check("INT-016: diff review type correct", report["type"] == "diff_review")


def test_syntax_error_resilience():
    """Agent should not crash on syntactically invalid code."""
    agent = CodeReviewAgent(use_ai=False)
    code = "def broken(\n    pass\nclass {"
    report = agent.review_source(code, "broken.py")
    check("INT-017: agent handles syntax errors gracefully", report["type"] == "file_review")


def test_empty_file():
    """Empty file should produce a report with no critical issues."""
    agent = CodeReviewAgent(use_ai=False)
    report = agent.review_source("", "empty.py")
    critical = [i for i in report["issues"] if i["severity"] == "CRITICAL"]
    check("INT-018: empty file has no CRITICAL issues", len(critical) == 0)


def test_format_report_no_crash():
    """format_report should not crash."""
    from code_review_agent import format_report

    agent = CodeReviewAgent(use_ai=False)
    report = agent.review_source('eval(input())\n', "t.py")
    text = format_report(report, colorize=False)
    check("INT-019: format_report returns string", isinstance(text, str))
    check("INT-020: format_report contains issue info", "eval" in text.lower())


# ===================================================================
# EDGE CASE TESTS
# ===================================================================

def test_multiline_string_not_secret():
    """Multi-line strings should not be flagged as secrets."""
    code = textwrap.dedent('''\
        description = """
        This is a long description that happens to mention
        the word password in a sentence but is not a secret.
        """
    ''')
    issues = check_hardcoded_secrets(code, "test.py")
    check("EDGE-001: multiline docstring NOT flagged as secret", len(issues) == 0)


def test_comment_with_eval_ok():
    """eval in a comment should not trigger."""
    code = "# Don't use eval() here\n"
    issues = check_eval_exec(code, "test.py")
    check("EDGE-002: eval in comment NOT flagged", len(issues) == 0)


def test_multiple_issues_same_line():
    """Multiple rules can fire on the same line."""
    code = 'password = "abc12345"; result = eval(password)\n'
    issues = run_all_rules(code, "test.py")
    rules = {i["rule"] for i in issues}
    has_secret = "hardcoded-secret" in rules
    has_eval = "eval-exec" in rules
    check("EDGE-003: multiple rules fire on same line", has_secret and has_eval)


def test_large_file_performance():
    """Agent should handle a large file without crashing."""
    agent = CodeReviewAgent(use_ai=False)
    code = "\n".join([f"x_{i} = {i}" for i in range(5000)])
    report = agent.review_source(code, "large.py")
    check("EDGE-004: handles 5000-line file", report["type"] == "file_review")


# ===================================================================
# Runner
# ===================================================================

def run_all_tests():
    """Run all test functions and compute accuracy."""
    # Exclude this meta-runner itself to avoid infinite recursion
    test_functions = [
        v for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v) and k != "test_overall_accuracy"
    ]

    print(f"\nRunning {len(test_functions)} test functions...\n")

    for fn in test_functions:
        try:
            fn()
        except Exception as e:
            results.append(TestResult(fn.__name__, False, f"EXCEPTION: {e}"))

    # Print results
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)
    accuracy = (passed / total * 100) if total else 0

    print(f"{'=' * 60}")
    print(f"  AI Code Review Agent — Test Results")
    print(f"{'=' * 60}\n")

    for r in results:
        status = "\033[92mPASS\033[0m" if r.passed else "\033[91mFAIL\033[0m"
        print(f"  [{status}] {r.name}")
        if not r.passed and r.detail:
            print(f"         {r.detail}")

    print(f"\n{'=' * 60}")
    print(f"  Total: {total}  |  Passed: {passed}  |  Failed: {failed}")
    print(f"  Accuracy: {accuracy:.1f}%")

    if accuracy >= 98:
        print(f"  \033[92m✓ ACCURACY TARGET MET (>= 98%)\033[0m")
    else:
        print(f"  \033[91m✗ ACCURACY TARGET NOT MET (< 98%)\033[0m")

    print(f"{'=' * 60}\n")

    return accuracy >= 98


# pytest compatibility
def test_overall_accuracy():
    """Meta-test: ensure overall accuracy is >= 98%."""
    run_all_tests()
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    accuracy = (passed / total * 100) if total else 0
    assert accuracy >= 98, f"Accuracy {accuracy:.1f}% is below 98% target"


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
