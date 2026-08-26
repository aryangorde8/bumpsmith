"""A one-tool MCP server whose tool must never run.

`open_pull_request` is annotated `destructiveHint: true`, which is what TrueForge's
default `require_approval_for_tools` (["@write", "@destructive"]) selects on. So the
harness pauses the call with no special configuration at all.

If the tool is ever actually invoked it appends to CALLS *and* keeps the call in
memory, where ``GET /calls`` will report it. Nothing existing at the end of the
run is the evidence that the deny stopped the effect rather than merely being
recorded next to it.

Two ways of asking because they fail differently. The file is durable and can be
inspected afterwards, but it lives at a path this process chose and a checker
that looked somewhere else would find nothing and call it a pass. ``GET /calls``
cannot be wrong about which process it asked: ``deny.py`` reads the URL out of
the harness's own MCP manifest, so the server it questions is the server the
harness would have called.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CALLS = Path(sys.argv[2] if len(sys.argv) > 2 else "pr-calls.log")
PORT = int(sys.argv[1] if len(sys.argv) > 1 else 8791)

CALLED: list[object] = []
"""Every tools/call this process has served, for `GET /calls` to report."""

TOOLS = [
    {
        "name": "open_pull_request",
        "description": (
            "Open a pull request on a GitHub repository. Irreversible: the branch is "
            "pushed and the pull request becomes visible to everyone with repo access."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string", "description": "owner/name"},
                "branch": {"type": "string", "description": "head branch to push"},
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["repository", "branch", "title"],
        },
        "annotations": {
            "title": "Open a pull request",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    }
]


def handle(message: dict[str, object]) -> dict[str, object] | None:
    method = message.get("method")
    mid = message.get("id")
    if mid is None:
        return None  # a notification
    if not isinstance(method, str):
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "error": {"code": -32600, "message": "a request needs a method name"},
        }
    if method == "initialize":
        params = message.get("params")
        asked = params.get("protocolVersion") if isinstance(params, dict) else None
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": asked if isinstance(asked, str) else "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "irreversible-things", "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params")
        CALLED.append(params)
        with CALLS.open("a", encoding="utf-8") as handle_:
            handle_.write(json.dumps(params) + "\n")
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "content": [{"type": "text", "text": "pull request opened"}],
                "isError": False,
            },
        }
    if method in {"resources/list", "prompts/list"}:
        key = "resources" if method.startswith("resources") else "prompts"
        return {"jsonrpc": "2.0", "id": mid, "result": {key: []}}
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"no method {method!r}"},
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("mcp %s\n" % (fmt % args))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return
        batch = body if isinstance(body, list) else [body]
        replies = [r for r in (handle(m) for m in batch if isinstance(m, dict)) if r is not None]
        if not replies:
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        payload = json.dumps(replies if isinstance(body, list) else replies[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        """``/calls`` reports what this server actually ran. Everything else is 405.

        Not part of MCP. It exists so that the deny proof can ask the server the
        harness is configured to call, rather than inspecting a file at a path
        the two of them might not agree on.
        """
        if self.path.rstrip("/") != "/calls":
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        payload = json.dumps({"calls": CALLED}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_DELETE(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
