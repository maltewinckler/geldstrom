#!/usr/bin/env python3
"""Query available TAN methods from a bank.

Usage:
    python examples/check_tan_methods.py [--env-file .env] [-v]

Queries the bank for supported TAN methods. This uses the sync dialog
which does NOT require TAN approval - useful for discovering available
methods before choosing one.

According to FinTS specification:
- Sync dialog fetches BPD (Bank Parameter Data) with one-step auth
- HITANS segments contain TAN method definitions
- Each method has a security function code, name, and capabilities
"""

from __future__ import annotations

import argparse

from _common import (
    add_common_args,
    create_client,
    load_env,
    print_footer,
    print_header,
    print_separator,
    setup_logging,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query available TAN methods")
    add_common_args(parser)
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)

    print_header("🏦 TAN METHODS QUERY")
    print(f"\nBank: {env.get('FINTS_BLZ')}")
    print(f"User: {env.get('FINTS_USER')}")
    print("\nNote: This query uses one-step auth (no TAN approval needed).")

    print_separator()
    print("Fetching TAN methods via sync dialog...")

    # Create client - get_tan_methods() doesn't require full connection
    client = create_client(env)
    methods = client.get_tan_methods()
    print(f"Found {len(methods)} TAN method(s).\n")

    if not methods:
        print("❌ No TAN methods found. The bank may require different authentication.")
        return

    print_header("TAN METHODS")

    for method in methods:
        print(f"\n  Code: {method.code}")
        print(f"  Name: {method.name}")
        print(f"  Type: {method.method_type.value}")

        if method.technical_id:
            print(f"  Technical ID: {method.technical_id}")
        if method.zka_id:
            print(f"  ZKA ID: {method.zka_id} (v{method.zka_version})")
        if method.is_decoupled:
            print(f"  Decoupled: Yes (max {method.decoupled_max_polls} polls)")
            if method.decoupled_first_poll_delay:
                print(f"  First poll delay: {method.decoupled_first_poll_delay}s")
            if method.decoupled_poll_interval:
                print(f"  Poll interval: {method.decoupled_poll_interval}s")
        if method.max_tan_length:
            print(f"  Max TAN length: {method.max_tan_length}")
        if method.supports_cancel:
            print("  Supports cancel: Yes")
        if method.supports_multiple_tan:
            print("  Supports multiple TAN: Yes")

    print()
    print_separator()
    print("\n📋 Summary:\n")
    print("| Code | Name                          | Type        |")
    print("|------|-------------------------------|-------------|")
    for method in methods:
        name = method.name[:29] if len(method.name) > 29 else method.name
        method_type = method.method_type.value
        print(f"| {method.code:>4} | {name:<29} | {method_type:<11} |")

    print()
    print_footer()
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

