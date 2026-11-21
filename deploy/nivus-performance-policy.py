#!/usr/bin/env python3
"""Systemd entry point for the opt-in, host-side power policy."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telemetry.power_policy import CONFIG_PATH, PowerPolicyError, apply_policy, load_config


def main() -> int:
    try:
        config = load_config(CONFIG_PATH, require_root_owner=True)
        result = apply_policy(config)
    except (OSError, PowerPolicyError) as exc:
        # Exception text is a fixed policy error, not a path, secret, or UPS response.
        print(f"Nivus power policy not applied: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
