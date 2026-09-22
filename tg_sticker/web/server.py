"""Lightweight embedded HTTP server for the Telegram Sticker Converter Web UI."""

from __future__ import annotations

import cgi
import errno
import http.server
import json
import os
import shutil
import socketserver
import tempfile
import urllib.parse
from pathlib import Path

from tg_sticker.batch import process_batch
from tg_sticker.converter import ConversionConfig, TelegramConverter
from tg_sticker.exceptions import TelegramStickerError
from tg_sticker.utils.logger import logger

STATIC_DIR = Path(__file__).parent / "static"
TEMP_DIR = Path(tempfile.gettempdir()) / "tg_sticker_web"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


class StickerRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self._send_json(
                {"status": "ok", "message": "Telegram Sticker Converter Ready"}
            )
            return

        elif path.startswith("/output/"):
            # Serve generated webm files
            filename = os.path.basename(path)
            file_path = TEMP_DIR / filename
            if file_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "video/webm")
                self.send_header("Content-Length", str(file_path.stat().st_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(file_path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
                return
            else:
                self.send_error(404, "File not found")
                return

        elif path == "/api/folders":
            in_dir = Path("input_videos").resolve()
            out_dir = Path("output_stickers").resolve()
            in_files = (
                [f.name for f in in_dir.glob("*") if f.is_file()]
                if in_dir.exists()
                else []
            )
            out_files = (
                [f.name for f in out_dir.glob("*.webm") if f.is_file()]
                if out_dir.exists()
                else []
            )
            self._send_json(
                {
                    "input_dir": str(in_dir),
                    "output_dir": str(out_dir),
                    "input_files": in_files,
                    "output_files": out_files,
                }
            )
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/convert":
            self._handle_convert()
        elif path == "/api/batch":
            self._handle_batch()
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_convert(self):
        try:
            ctype, pdict = cgi.parse_header(self.headers.get("content-type"))
            if ctype != "multipart/form-data":
                self._send_json({"error": "Expected multipart/form-data"}, status=400)
                return

            pdict["boundary"] = bytes(pdict["boundary"], "ascii")
            pdict["CONTENT-LENGTH"] = int(self.headers.get("content-length", 0))

            form = cgi.parse_multipart(self.rfile, pdict)

            file_data = form.get("video")
            if not file_data or len(file_data) == 0:
                self._send_json({"error": "No video file uploaded"}, status=400)
                return

            video_bytes = file_data[0]
            filename = form.get("filename", ["uploaded_video.mp4"])[0]

            mode = form.get("mode", ["sticker"])[0]
            start_str = form.get("start_time", [""])[0]
            start_time = float(start_str) if start_str else None

            dur_str = form.get("duration", [""])[0]
            duration = float(dur_str) if dur_str else None

            speed_to_fit = form.get("speed_to_fit", ["false"])[0].lower() == "true"
            loop_mode = form.get("loop_mode", ["normal"])[0]
            fit_mode_raw = form.get("fit_mode", [""])[0]
            fit_mode = (
                fit_mode_raw
                if fit_mode_raw in ("contain", "crop", "pad", "stretch")
                else None
            )
            remove_bg = form.get("remove_bg", [""])[0] or None
            fps_str = form.get("fps", ["30"])[0]
            fps = min(int(fps_str), 30) if fps_str else 30
            crf_str = form.get("crf", ["30"])[0]
            crf = max(0, min(int(crf_str), 63)) if crf_str else 30
            preserve_alpha = form.get("preserve_alpha", ["true"])[0].lower() == "true"

            # Save input to temp file
            in_ext = Path(filename).suffix or ".mp4"
            in_temp = TEMP_DIR / f"upload_{os.getpid()}_{hash(filename)}{in_ext}"
            with open(in_temp, "wb") as f:
                f.write(video_bytes)

            out_stem = Path(filename).stem
            out_filename = f"{out_stem}_telegram.webm"
            out_temp = TEMP_DIR / out_filename

            cfg = ConversionConfig(
                mode=mode,
                start_time=start_time,
                duration=duration,
                speed_to_fit=speed_to_fit,
                loop_mode=loop_mode,
                fit_mode=fit_mode,
                fps=fps,
                crf=crf,
                remove_bg=remove_bg,
                preserve_alpha=preserve_alpha,
            )

            converter = TelegramConverter()
            result = converter.convert(in_temp, out_temp, config=cfg)

            info = result.info
            self._send_json(
                {
                    "success": True,
                    "valid": result.valid,
                    "issues": result.issues,
                    "download_url": f"/output/{out_filename}",
                    "filename": out_filename,
                    "info": {
                        "width": info.width,
                        "height": info.height,
                        "duration": info.duration,
                        "fps": info.fps,
                        "size_bytes": info.size_bytes,
                        "size_kb": info.size_kb,
                        "codec": info.video_codec,
                        "has_audio": info.has_audio,
                        "has_alpha": info.has_alpha,
                    }
                    if info
                    else None,
                }
            )
        except TelegramStickerError as e:
            self._send_json(
                {"error": str(e), "error_type": e.__class__.__name__}, status=400
            )
        except Exception as e:
            self._send_json(
                {
                    "error": f"Internal server error: {e}",
                    "error_type": "InternalServerError",
                },
                status=500,
            )

    def _handle_batch(self):
        try:
            content_len = int(self.headers.get("content-length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            params = json.loads(body) if body else {}

            mode = params.get("mode", "sticker")
            duration = float(params["duration"]) if params.get("duration") else None
            speed_to_fit = bool(params.get("speed_to_fit", False))
            loop_mode = params.get("loop_mode", "normal")
            fit_mode_raw = params.get("fit_mode")
            fit_mode = (
                fit_mode_raw
                if fit_mode_raw in ("contain", "crop", "pad", "stretch")
                else None
            )
            fps = min(int(params.get("fps", 30)), 30)
            crf = max(0, min(int(params.get("crf", 30)), 63))
            remove_bg = params.get("remove_bg") or None
            preserve_alpha = bool(params.get("preserve_alpha", True))
            overwrite = bool(params.get("overwrite", False))
            recursive = bool(params.get("recursive", False))

            cfg = ConversionConfig(
                mode=mode,
                duration=duration,
                speed_to_fit=speed_to_fit,
                loop_mode=loop_mode,
                fit_mode=fit_mode,
                fps=fps,
                crf=crf,
                remove_bg=remove_bg,
                preserve_alpha=preserve_alpha,
            )

            summary = process_batch(
                input_dir="input_videos",
                output_dir="output_stickers",
                config=cfg,
                overwrite=overwrite,
                recursive=recursive,
            )

            self._send_json(
                {
                    "success": True,
                    "total": summary.total,
                    "succeeded": summary.succeeded,
                    "skipped": summary.skipped,
                    "failed": summary.failed,
                }
            )
        except TelegramStickerError as e:
            self._send_json(
                {"error": str(e), "error_type": e.__class__.__name__}, status=400
            )
        except Exception as e:
            self._send_json(
                {
                    "error": f"Internal server error: {e}",
                    "error_type": "InternalServerError",
                },
                status=500,
            )

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server(host: str = "127.0.0.1", port: int = 8080):
    server_address = (host, port)
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(server_address, StickerRequestHandler) as httpd:
            logger.divider(length=50)
            logger.info("  Telegram Sticker Converter Web UI Running at:")
            logger.info("  http://%s:%d/", host, port)
            logger.divider(length=50)
            logger.info("Press Ctrl+C to stop the server.")
            httpd.serve_forever()
    except OSError as e:
        is_port_in_use = (
            getattr(e, "errno", None) in (errno.EADDRINUSE, 10048)
            or getattr(e, "winerror", None) == 10048
            or "already in use" in str(e).lower()
            or "normally permitted" in str(e).lower()
        )
        if is_port_in_use:
            fallback_port = port + 1
            logger.warn("Port %d busy, attempting port %d...", port, fallback_port)
            start_server(host=host, port=fallback_port)
        else:
            raise
