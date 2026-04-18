#!/usr/bin/env python3
"""MCP Content Server - A Model Context Protocol server for writing content.

Provides tools for creating, editing, organizing, and managing written content
such as blog posts, articles, social media posts, emails, and more.
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# MCP protocol constants
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "content-writer"
SERVER_VERSION = "1.0.0"

# Content storage directory
CONTENT_DIR = Path(os.environ.get("CONTENT_DIR", os.path.join(os.path.dirname(__file__), "content")))


def ensure_content_dir():
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)


def read_message():
    """Read a JSON-RPC message from stdin using the MCP transport protocol."""
    headers = {}
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        line = line.rstrip("\r\n")
        if line == "":
            if headers:
                break
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    content_length = int(headers.get("content-length", 0))
    if content_length == 0:
        return None
    body = sys.stdin.read(content_length)
    return json.loads(body)


def send_message(msg):
    """Send a JSON-RPC message to stdout using the MCP transport protocol."""
    body = json.dumps(msg)
    sys.stdout.write(f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n")  # MCP stdio transport
    sys.stdout.write(body)
    sys.stdout.flush()


def send_result(request_id, result):
    send_message({"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result})


def send_error(request_id, code, message):
    send_message({
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {"code": code, "message": message},
    })


# --- Content management helpers ---

def _content_path(content_id):
    return CONTENT_DIR / f"{content_id}.json"


def _load_content(content_id):
    path = _content_path(content_id)
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


def _save_content(content_id, data):
    ensure_content_dir()
    with open(_content_path(content_id), "w") as f:
        json.dump(data, f, indent=2)


def _list_all_content():
    ensure_content_dir()
    items = []
    for p in sorted(CONTENT_DIR.glob("*.json")):
        with open(p) as f:
            items.append(json.load(f))
    return items


# --- Tool definitions ---

TOOLS = [
    {
        "name": "create_content",
        "description": "Create a new piece of content (article, blog post, email, social media post, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the content"},
                "body": {"type": "string", "description": "The main body/text of the content"},
                "content_type": {
                    "type": "string",
                    "description": "Type of content",
                    "enum": ["article", "blog_post", "email", "social_media", "newsletter", "documentation", "other"],
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags/categories for the content",
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "review", "published"],
                    "description": "Status of the content (default: draft)",
                },
            },
            "required": ["title", "body"],
        },
    },
    {
        "name": "edit_content",
        "description": "Edit an existing piece of content by ID. You can update the title, body, tags, or status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content_id": {"type": "string", "description": "The ID of the content to edit"},
                "title": {"type": "string", "description": "New title (optional)"},
                "body": {"type": "string", "description": "New body text (optional)"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags (optional)"},
                "status": {
                    "type": "string",
                    "enum": ["draft", "review", "published"],
                    "description": "New status (optional)",
                },
            },
            "required": ["content_id"],
        },
    },
    {
        "name": "get_content",
        "description": "Retrieve a piece of content by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content_id": {"type": "string", "description": "The ID of the content to retrieve"},
            },
            "required": ["content_id"],
        },
    },
    {
        "name": "list_content",
        "description": "List all saved content, optionally filtered by type, status, or tag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content_type": {"type": "string", "description": "Filter by content type"},
                "status": {"type": "string", "description": "Filter by status"},
                "tag": {"type": "string", "description": "Filter by tag"},
            },
        },
    },
    {
        "name": "delete_content",
        "description": "Delete a piece of content by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content_id": {"type": "string", "description": "The ID of the content to delete"},
            },
            "required": ["content_id"],
        },
    },
    {
        "name": "search_content",
        "description": "Search content by keyword in title or body.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query to match against title and body"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "export_content",
        "description": "Export a piece of content to markdown or plain text format.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content_id": {"type": "string", "description": "The ID of the content to export"},
                "format": {
                    "type": "string",
                    "enum": ["markdown", "plaintext", "html"],
                    "description": "Export format (default: markdown)",
                },
            },
            "required": ["content_id"],
        },
    },
]

# --- Tool handlers ---


def handle_create_content(args):
    content_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat() + "Z"
    data = {
        "id": content_id,
        "title": args["title"],
        "body": args["body"],
        "content_type": args.get("content_type", "other"),
        "tags": args.get("tags", []),
        "status": args.get("status", "draft"),
        "created_at": now,
        "updated_at": now,
    }
    _save_content(content_id, data)
    return [{"type": "text", "text": f"Content created with ID: {content_id}\n\n{json.dumps(data, indent=2)}"}]


def handle_edit_content(args):
    content_id = args["content_id"]
    data = _load_content(content_id)
    if not data:
        return [{"type": "text", "text": f"Error: Content with ID '{content_id}' not found."}]

    for field in ("title", "body", "tags", "status"):
        if field in args:
            data[field] = args[field]
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save_content(content_id, data)
    return [{"type": "text", "text": f"Content updated.\n\n{json.dumps(data, indent=2)}"}]


def handle_get_content(args):
    data = _load_content(args["content_id"])
    if not data:
        return [{"type": "text", "text": f"Error: Content with ID '{args['content_id']}' not found."}]
    return [{"type": "text", "text": json.dumps(data, indent=2)}]


def handle_list_content(args):
    items = _list_all_content()
    if args.get("content_type"):
        items = [i for i in items if i.get("content_type") == args["content_type"]]
    if args.get("status"):
        items = [i for i in items if i.get("status") == args["status"]]
    if args.get("tag"):
        items = [i for i in items if args["tag"] in i.get("tags", [])]

    if not items:
        return [{"type": "text", "text": "No content found."}]

    summary = []
    for item in items:
        summary.append(f"- [{item['id']}] {item['title']} ({item['content_type']}, {item['status']})")
    return [{"type": "text", "text": f"Found {len(items)} item(s):\n" + "\n".join(summary)}]


def handle_delete_content(args):
    content_id = args["content_id"]
    path = _content_path(content_id)
    if not path.exists():
        return [{"type": "text", "text": f"Error: Content with ID '{content_id}' not found."}]
    path.unlink()
    return [{"type": "text", "text": f"Content '{content_id}' deleted."}]


def handle_search_content(args):
    query = args["query"].lower()
    items = _list_all_content()
    matches = [
        i for i in items
        if query in i.get("title", "").lower() or query in i.get("body", "").lower()
    ]
    if not matches:
        return [{"type": "text", "text": f"No content matching '{args['query']}'."}]

    summary = []
    for item in matches:
        summary.append(f"- [{item['id']}] {item['title']} ({item['content_type']}, {item['status']})")
    return [{"type": "text", "text": f"Found {len(matches)} match(es):\n" + "\n".join(summary)}]


def handle_export_content(args):
    data = _load_content(args["content_id"])
    if not data:
        return [{"type": "text", "text": f"Error: Content with ID '{args['content_id']}' not found."}]

    fmt = args.get("format", "markdown")
    tags_str = ", ".join(data.get("tags", []))

    if fmt == "markdown":
        output = f"# {data['title']}\n\n"
        if tags_str:
            output += f"**Tags:** {tags_str}\n\n"
        output += f"**Status:** {data['status']} | **Type:** {data['content_type']}\n\n---\n\n"
        output += data["body"]
    elif fmt == "html":
        output = f"<h1>{data['title']}</h1>\n"
        if tags_str:
            output += f"<p><strong>Tags:</strong> {tags_str}</p>\n"
        output += f"<p><em>{data['status']} | {data['content_type']}</em></p>\n<hr>\n"
        output += f"<div>{data['body']}</div>"
    else:
        output = f"{data['title']}\n{'=' * len(data['title'])}\n\n"
        if tags_str:
            output += f"Tags: {tags_str}\n"
        output += f"Status: {data['status']} | Type: {data['content_type']}\n\n"
        output += data["body"]

    return [{"type": "text", "text": output}]


TOOL_HANDLERS = {
    "create_content": handle_create_content,
    "edit_content": handle_edit_content,
    "get_content": handle_get_content,
    "list_content": handle_list_content,
    "delete_content": handle_delete_content,
    "search_content": handle_search_content,
    "export_content": handle_export_content,
}


# --- MCP request handling ---


def handle_request(msg):
    method = msg.get("method")
    request_id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        send_result(request_id, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
    elif method == "notifications/initialized":
        pass  # no response needed
    elif method == "tools/list":
        send_result(request_id, {"tools": TOOLS})
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)
        if handler:
            try:
                content = handler(arguments)
                send_result(request_id, {"content": content})
            except Exception as e:
                send_result(request_id, {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True,
                })
        else:
            send_error(request_id, -32601, f"Unknown tool: {tool_name}")
    elif method == "ping":
        send_result(request_id, {})
    else:
        if request_id is not None:
            send_error(request_id, -32601, f"Method not found: {method}")


def main():
    """Run the MCP content server using stdio transport."""
    while True:
        try:
            msg = read_message()
            if msg is None:
                break
            handle_request(msg)
        except (EOFError, BrokenPipeError):
            break
        except Exception as e:
            sys.stderr.write(f"Server error: {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
