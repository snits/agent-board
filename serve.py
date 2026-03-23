# ABOUTME: Convenience script that preprocesses data then serves the frontend.
# ABOUTME: Usage: python serve.py [--source PATH] [--port PORT]

import argparse
import http.server
import socketserver
from pathlib import Path

from preprocessor.config import load_config
from preprocessor.paths import default_archive_dir, default_data_dir, default_source_dir
from preprocessor.pipeline import run_preprocess


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves frontend from project root and /data/ from the XDG data directory."""

    data_dir: Path = Path("data")

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.send_response(302)
            self.send_header("Location", "/frontend/")
            self.end_headers()
            return
        super().do_GET()

    def translate_path(self, path):
        """Route /data/ requests to the XDG data directory."""
        if path.startswith("/data/") or path == "/data":
            relative = path[len("/data"):]
            if relative.startswith("/"):
                relative = relative[1:]
            resolved = (self.data_dir / relative).resolve()
            if not resolved.is_relative_to(self.data_dir.resolve()):
                return str(self.data_dir)
            return str(resolved)
        return super().translate_path(path)

    def log_request(self, code="-", size="-"):
        if isinstance(code, int) and code >= 400:
            super().log_request(code, size)


def main():
    parser = argparse.ArgumentParser(description="Preprocess and serve Agent Board")
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--skip-preprocess", action="store_true", help="Skip preprocessing, serve existing data")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--tui", action="store_true", help="Launch terminal UI instead of web server")
    args = parser.parse_args()
    config = load_config()
    args.source = args.source if args.source is not None else config.get("source", default_source_dir())
    args.port = args.port if args.port is not None else config.get("port", 8080)
    args.output = args.output if args.output is not None else default_data_dir()

    if not args.skip_preprocess:
        if not args.source.exists():
            print(f"Error: source directory not found: {args.source}")
            print("Use --source to specify the Claude projects directory, or --skip-preprocess to serve existing data.")
            raise SystemExit(1)
        print("Preprocessing transcripts...")
        run_preprocess(args.source, args.output, archive_dir=default_archive_dir())
        print()

    if args.tui:
        from tui.app import AgentBoardApp
        AgentBoardApp(data_dir=args.output, source_dir=args.source).run()
        return

    project_root = str(Path(__file__).parent)
    socketserver.TCPServer.allow_reuse_address = True
    Handler.data_dir = args.output.resolve()

    with socketserver.TCPServer(("", args.port), lambda *a, **kw: Handler(*a, directory=project_root, **kw)) as httpd:
        print(f"Agent Board running at http://localhost:{args.port}/frontend/")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server.")


if __name__ == "__main__":
    main()
