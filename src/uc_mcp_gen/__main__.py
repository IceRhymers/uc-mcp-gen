"""uc-mcp-gen CLI entry point."""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("uc-mcp-gen")

    parser = argparse.ArgumentParser(
        prog="uc-mcp-gen",
        description="uc-mcp-gen — generate Databricks App bundles from OpenAPI specs",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── generate ─────────────────────────────────────────────
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate a self-contained Databricks App bundle from an OpenAPI spec",
    )
    gen_parser.add_argument("spec", help="Path or URL to OpenAPI spec (JSON or YAML)")
    gen_parser.add_argument("--connection", required=True, help="UC connection name")
    gen_parser.add_argument("--name", default=None, help="Service name (default: derived from spec title)")
    gen_parser.add_argument("-o", "--output", default=None, help="Output directory")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        from uc_mcp_gen.codegen.generator import generate

        try:
            result = generate(
                args.spec,
                args.connection,
                service_name=args.name,
                output_dir=args.output,
            )
            print(f"Generated: {result}")
        except (FileNotFoundError, ValueError) as exc:
            logger.error(str(exc))
            sys.exit(1)


if __name__ == "__main__":
    main()
