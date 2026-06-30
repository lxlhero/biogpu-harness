#!/usr/bin/env python3
"""
PreToolUse hook: check rjob submit commands for inline bash compliance.

Reads tool input JSON from stdin (Claude Code hook protocol).
Exits 2 with a message to block execution if a violation is found.
Exits 0 to allow execution.

Violations caught:
  - rjob submit ... -- bash /path/to/script.sh   (script file entrypoint)
  - rjob name containing uppercase or underscore
"""

import json
import re
import sys


SCRIPT_ENTRYPOINT = re.compile(
    r'rjob\s+submit\b.*?--\s+bash\s+(?!-c\b)([^\s\'"]+\.sh)',
    re.DOTALL,
)

INLINE_MISSING = re.compile(
    r'rjob\s+submit\b.*?--\s+bash\s+[^\-]',
    re.DOTALL,
)

NAME_VIOLATION = re.compile(
    r'--name[= ](\S+)',
)


def check(command: str) -> list[str]:
    violations = []

    if 'rjob' not in command or 'submit' not in command:
        return violations

    # Check for script file entrypoint
    m = SCRIPT_ENTRYPOINT.search(command)
    if m:
        violations.append(
            f"⛔ rjob 铁律违反: entrypoint 是脚本文件 '{m.group(1)}'。"
            " 必须使用内联 bash: -- bash -c '...'"
        )

    # Check for bash without -c (e.g. -- bash /path/something)
    # Look for the pattern: rjob submit ... -- bash <non-dash>
    # but allow -- bash -c
    if re.search(r'--\s+bash\s+[^-\s\'"]', command):
        violations.append(
            "⛔ rjob 铁律违反: '-- bash' 后面不是 '-c'。"
            " 必须是 -- bash -c '...'"
        )

    # Check name violations
    for m in NAME_VIOLATION.finditer(command):
        name = m.group(1).strip("'\"")
        if re.search(r'[A-Z_]', name):
            violations.append(
                f"⛔ rjob 名称违规: '{name}' 含大写字母或下划线。"
                " 只能用小写字母、数字、连字符。"
            )

    return violations


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # not a JSON hook call, allow

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only check Bash tool calls
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    violations = check(command)
    if violations:
        msg = "\n".join(violations)
        print(f"\n{msg}\n", file=sys.stderr)
        # Exit code 2 = block the tool call and show message to user
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
