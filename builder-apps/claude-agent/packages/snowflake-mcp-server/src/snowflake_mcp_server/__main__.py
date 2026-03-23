"""Run the Snowflake MCP server via stdio.

Usage:
    python -m snowflake_mcp_server
"""

from snowflake_mcp_server.server import create_stdio_server


def main():
    server = create_stdio_server()
    server.run()


if __name__ == "__main__":
    main()
