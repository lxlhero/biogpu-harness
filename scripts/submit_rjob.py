#!/usr/bin/env python3
"""
BioGPU-Harness rjob submission builder.

Generates a validated rjob submit command with configurable namespace/mount.
Enforces inline bash — refuses to accept script file paths.

Usage:
  python scripts/submit_rjob.py \
    --name gsmap-profiling \
    --image registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu/gsmap-gpu:l1-cpu \
    --gpu 1 --cpu 32 --memory 204800 \
    --inline-cmd 'gsmap run_find_latent_representations ...'

  Or pipe the inline command via --stdin-cmd:
    echo 'gsmap ...' | python scripts/submit_rjob.py --name foo --image bar --stdin-cmd
"""

import argparse
import os
import re
import sys
import json


DEFAULT_NAMESPACE = "ailab-ma4agismall"
DEFAULT_CHARGED_GROUP = "ma4agismall_gpu"
DEFAULT_MOUNT = "gpfs://gpfs2/liangxiuliang-2:/mnt/shared-storage-gpfs2/liangxiuliang-2"
DEFAULT_IMAGE_PULL_POLICY = "IfNotPresent"


SCRIPT_PATTERN = re.compile(
    r"""
    (?:^|[;\|&]\s*)          # start or after ; | &
    bash\s+                   # bash keyword
    (?!-c\b)                  # not -c flag
    [^\s'"]+\.sh              # a .sh file path
    """,
    re.VERBOSE | re.MULTILINE,
)


def check_inline(cmd: str) -> list[str]:
    """Return list of violations if cmd uses script files instead of inline bash."""
    violations = []
    matches = SCRIPT_PATTERN.findall(cmd)
    if matches:
        violations.append(
            f"rjob command contains shell script execution: {matches}. "
            "Must use inline bash: -- bash -c '...'"
        )
    # Also catch: -- bash /path/to/something.sh
    if re.search(r'--\s+bash\s+[^\-\s\'"][^\s\'"]*\.sh', cmd):
        violations.append(
            "rjob entrypoint is a .sh file. Must be: -- bash -c '...'"
        )
    return violations


def build_command(args) -> str:
    """Build the full rjob submit command string."""
    parts = ["rjob submit"]

    # Job identity
    parts.append(f"  --name={args.name}")
    parts.append(f"  --namespace={args.namespace}")

    # Resources
    parts.append(f"  --charged-group={args.charged_group}")
    parts.append("  --private-machine=group")
    if args.gpu > 0:
        parts.append(f"  --gpu={args.gpu}")
    parts.append(f"  --cpu={args.cpu}")
    parts.append(f"  --memory={args.memory}")

    # Image
    parts.append(f"  --image={args.image}")
    parts.append(f"  --image-pull-policy={args.image_pull_policy}")

    # Mount
    for mount in args.mount:
        parts.append(f"  --mount={mount}")

    # Extra env vars
    for env in (args.env or []):
        parts.append(f"  -e {env}")

    # Inline command
    inline = args.inline_cmd.strip()
    parts.append(f"  -- bash -c '\n{inline}\n'")

    return " \\\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Build and validate rjob submit command")
    parser.add_argument("--name", required=True, help="rjob name (lowercase, no underscore)")
    parser.add_argument("--image", required=True, help="Container image full path")
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--cpu", type=int, default=16)
    parser.add_argument("--memory", type=int, default=102400, help="Memory in MiB")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--charged-group", dest="charged_group", default=DEFAULT_CHARGED_GROUP)
    parser.add_argument(
        "--mount", action="append", default=None,
        help="Mount spec (may repeat). Defaults to GPFS liangxiuliang-2."
    )
    parser.add_argument("--image-pull-policy", dest="image_pull_policy",
                        default=DEFAULT_IMAGE_PULL_POLICY)
    parser.add_argument("--env", "-e", action="append", help="KEY=VALUE env var (may repeat)")
    parser.add_argument("--inline-cmd", dest="inline_cmd", default=None,
                        help="The bash commands to run inline (required)")
    parser.add_argument("--stdin-cmd", action="store_true",
                        help="Read inline command from stdin")
    parser.add_argument("--check-only", action="store_true",
                        help="Only validate, don't print command")
    parser.add_argument("--json", action="store_true",
                        help="Output result as JSON")

    args = parser.parse_args()

    # Apply defaults
    if args.mount is None:
        args.mount = [DEFAULT_MOUNT]

    # Read inline command
    if args.stdin_cmd:
        args.inline_cmd = sys.stdin.read()
    if not args.inline_cmd:
        parser.error("--inline-cmd or --stdin-cmd is required")

    # Validate name
    name_violations = []
    if re.search(r'[A-Z_]', args.name):
        name_violations.append(
            f"rjob name '{args.name}' contains uppercase or underscore. Use lowercase + hyphens only."
        )

    # Validate inline
    cmd_violations = check_inline(args.inline_cmd)

    all_violations = name_violations + cmd_violations

    if args.json:
        out = {
            "status": "fail" if all_violations else "pass",
            "violations": all_violations,
        }
        if not all_violations and not args.check_only:
            out["command"] = build_command(args)
        print(json.dumps(out, indent=2))
    else:
        if all_violations:
            for v in all_violations:
                print(f"[RJOB-ERROR] {v}", file=sys.stderr)
        if not args.check_only and not all_violations:
            print(build_command(args))

    sys.exit(1 if all_violations else 0)


if __name__ == "__main__":
    main()
