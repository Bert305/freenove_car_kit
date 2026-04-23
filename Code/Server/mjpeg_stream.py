"""
MJPEG Browser Stream - Freenove 4WD Smart Car
==============================================
Serves the camera as a live MJPEG stream viewable in any browser on the
local network.  No app or extra software needed on the viewing device.

Run from the Code/Server/ directory:
    python mjpeg_stream.py

    
Then open  http://<pi-ip>:8080  in a browser on the same network.
The Pi's IP address is printed when the script starts.

Press Ctrl+C to stop.
"""

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from camera import Camera

# ── Config ─────────────────────────────────────────────────────────────────────
PORT          = 8080
STREAM_SIZE   = (640, 480)   # resolution served to the browser
BOUNDARY      = b'--jpegframe'
# ──────────────────────────────────────────────────────────────────────────────

camera: Camera = None   # set in run() before the server starts


def local_ip() -> str:
    """Best-effort LAN IP – falls back to localhost."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


PAGE_HTML = b"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Car Camera</title>
  <style>
    body  { margin:0; background:#111; display:flex; flex-direction:column;
            align-items:center; justify-content:center; height:100vh; }
    img   { max-width:100%; border:2px solid #444; border-radius:6px; }
    p     { color:#888; font-family:monospace; margin-top:10px; font-size:13px; }
  </style>
</head>
<body>
  <img src="/stream" alt="camera feed">
  <p>Freenove 4WD &mdash; live feed</p>
</body>
</html>"""

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence per-request console noise

    def do_GET(self):
        if self.path == '/':
            self._serve_page()
        elif self.path == '/stream':
            self._serve_stream()
        else:
            self.send_error(404)

    def _serve_page(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(PAGE_HTML)))
        self.end_headers()
        self.wfile.write(PAGE_HTML)

    def _serve_stream(self):
        self.send_response(200)
        self.send_header('Age', '0')
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type',
                         f'multipart/x-mixed-replace; boundary={BOUNDARY.decode()}')
        self.end_headers()
        try:
            while True:
                frame = camera.get_frame()
                header = (
                    BOUNDARY + b'\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(frame)).encode() + b'\r\n\r\n'
                )
                self.wfile.write(header + frame + b'\r\n')
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser tab closed or navigated away


def run():
    global camera

    print("Initialising camera...")
    camera = Camera(stream_size=STREAM_SIZE)
    camera.start_stream()

    server = HTTPServer(('', PORT), StreamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    ip = local_ip()
    print(f"\nStream live at  http://{ip}:{PORT}")
    print("Open that URL in any browser on the same Wi-Fi network.")
    print("Press Ctrl+C to stop.\n")

    try:
        thread.join()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.shutdown()
        camera.close()
        print("Done.")


if __name__ == '__main__':
    run()
