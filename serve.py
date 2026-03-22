# ABOUTME: Convenience script that preprocesses data then serves the frontend.
# ABOUTME: Usage: python serve.py [--source PATH] [--port PORT]

import argparse
import http.server
import socketserver
from pathlib import Path

from preprocess import run_preprocess


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves files from the project root and redirects / to /frontend/."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.send_response(302)
            self.send_header("Location", "/frontend/")
            self.end_headers()
            return
        super().do_GET()

    def log_request(self, code="-", size="-"):
        if isinstance(code, int) and code >= 400:
            super().log_request(code, size)


def main():
    parser = argparse.ArgumentParser(description="Preprocess and serve Agent Board")
    parser.add_argument("--source", type=Path, default=Path.home() / ".claude" / "projects")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--skip-preprocess", action="store_true", help="Skip preprocessing, serve existing data")
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()

    if not args.skip_preprocess:
        if not args.source.exists():
            print(f"Error: source directory not found: {args.source}")
            print("Use --source to specify the Claude projects directory, or --skip-preprocess to serve existing data.")
            raise SystemExit(1)
        print("Preprocessing transcripts...")
        run_preprocess(args.source, args.output)
        print()

    project_root = str(Path(__file__).parent)
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", args.port), lambda *a, **kw: Handler(*a, directory=project_root, **kw)) as httpd:
        print(f"Agent Board running at http://localhost:{args.port}/frontend/")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server.")


if __name__ == "__main__":
    main()
