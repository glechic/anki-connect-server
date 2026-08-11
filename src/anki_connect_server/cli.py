"""CLI entry point for anki-connect-server."""

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="anki-connect-server",
        description="Headless AnkiConnect-compatible REST API server with MCP support",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # API server subcommand
    subparsers.add_parser(
        "api",
        help="Run the AnkiConnect API server",
        description="Run the headless AnkiConnect-compatible REST API server.",
    )

    # MCP server subcommand
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Run the MCP server",
        description="Run the Model Context Protocol server for AI assistants.",
    )
    mcp_parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol: stdio (one process per client) or http "
        "(single long-lived server serving all clients). Default: stdio.",
    )

    args = parser.parse_args(argv)

    if args.command == "api":
        from anki_connect_server.api import run_server

        run_server()
    elif args.command == "mcp":
        from anki_connect_server.mcp_server import run

        run(transport=args.transport)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
