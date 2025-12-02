"""List and download bank statements.

Usage:
    python examples/fetch_statements.py [--download] [--output-dir DIR]

Lists available statements and optionally downloads them.
Note: Not all banks/accounts support statement retrieval.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from _common import (
    add_common_args,
    create_client,
    load_env,
    print_header,
    print_separator,
    setup_logging,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="List and download statements")
    add_common_args(parser)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download available statements",
    )
    parser.add_argument(
        "--output-dir",
        default="./statements",
        help="Output directory for downloads (default: ./statements)",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    env = load_env(args.env_file)

    print(f"Connecting to bank {env.get('FINTS_BLZ')}...")

    with create_client(env) as client:
        accounts = client.list_accounts()

        print_header("BANK STATEMENTS")

        for account in accounts:
            print(f"\n  Account: {account.iban or account.account_id}")
            print_separator(40)

            if not account.capabilities.can_fetch_statements:
                print("  Statements not supported for this account.")
                continue

            try:
                statements = client.list_statements(account)

                if not statements:
                    print("  No statements available.")
                    continue

                print(f"  Found {len(statements)} statement(s):")

                for i, stmt in enumerate(statements, 1):
                    stmt_num = getattr(stmt, "number", None) or i
                    stmt_date = getattr(stmt, "date", None) or "Unknown"

                    print(f"\n    {i}. Statement #{stmt_num}")
                    if stmt_date != "Unknown":
                        print(f"       Date: {stmt_date}")

                    if args.download:
                        try:
                            document = client.get_statement(stmt)
                            output_dir = Path(args.output_dir)
                            output_dir.mkdir(parents=True, exist_ok=True)

                            # Determine file extension
                            ext = ".pdf"
                            if document.mime_type:
                                if "xml" in document.mime_type.lower():
                                    ext = ".xml"
                                elif "text" in document.mime_type.lower():
                                    ext = ".txt"

                            filename = f"statement_{account.account_id}_{stmt_num}{ext}"
                            filepath = output_dir / filename
                            filepath.write_bytes(document.content)
                            print(f"       Saved: {filepath}")

                        except Exception as e:
                            print(f"       Download failed: {e}")

            except Exception as e:
                print(f"  Error listing statements: {e}")

        print()


if __name__ == "__main__":
    main()
