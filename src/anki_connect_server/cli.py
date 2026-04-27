"""CLI entry point for anki-connect-server."""
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        prog="anki-connect-server",
        description="Headless AnkiConnect-compatible REST API server with MCP support"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # API server subcommand
    api_parser = subparsers.add_parser("api", help="Run the AnkiConnect API server")
    
    # MCP server subcommand
    mcp_parser = subparsers.add_parser("mcp", help="Run the MCP server")
    
    args = parser.parse_args()
    
    if args.command == "api":
        from anki_connect_server.api import run_server
        run_server()
    elif args.command == "mcp":
        from anki_connect_server.mcp_server import run
        run()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
