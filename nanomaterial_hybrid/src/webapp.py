"""Local browser interface for the existing hybrid engine; no hosted services."""
from __future__ import annotations

import argparse
import json
import socket
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen
import webbrowser

from .predict import ROOT
from .recommend import RecommendationEngine,load_demo

APP_ID="nanoselect-local-v1"
WEB=ROOT / "web"


class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=False
    def server_bind(self):
        if hasattr(socket,"SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
    def __init__(self,address):
        super().__init__(address,Handler)
        self.engine=RecommendationEngine()
        self.engine_lock=threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _trusted(self):
        port=self.server.server_port
        allowed={f"127.0.0.1:{port}",f"localhost:{port}"}
        if self.headers.get("Host","") not in allowed:
            return False
        origin=self.headers.get("Origin")
        return not origin or origin in {f"http://{host}" for host in allowed}

    def _send(self,payload,status=200,content_type="application/json; charset=utf-8"):
        data=json.dumps(payload,allow_nan=False).encode() if content_type.startswith("application/json") else payload
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._trusted():
            return self._send({"error":"Use the local address printed in the terminal."},403)
        path=urlsplit(self.path).path
        if path=="/api/health":
            return self._send({"app_id":APP_ID,"status":"ready"})
        if path=="/api/meta":
            card=json.loads((ROOT / "models/model_card.json").read_text())
            return self._send({"pollutants":self.server.engine.pollutants.to_dict("records"),
                               "presets":{name:load_demo(name) for name in ["demo_ml","demo_dark","demo_lead","demo_unknown"]},
                               "model":{"name":card["model_name"],"mae":card["test_metrics"]["mae"],"r2":card["test_metrics"]["r2"]},
                               "material_count":len(self.server.engine.materials)})
        assets={"/":("index.html","text/html; charset=utf-8"),"/style.css":("style.css","text/css; charset=utf-8"),"/app.js":("app.js","text/javascript; charset=utf-8")}
        if path in assets:
            name,mime=assets[path]
            return self._send((WEB / name).read_bytes(),content_type=mime)
        self._send({"error":"Page not found."},404)

    def do_POST(self):
        if not self._trusted():
            return self._send({"error":"Only requests from this local interface are accepted."},403)
        if urlsplit(self.path).path!="/api/recommend":
            return self._send({"error":"Endpoint not found."},404)
        if self.headers.get("Content-Type","").split(";")[0]!="application/json":
            return self._send({"error":"Send inputs as JSON."},415)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if not 0<size<=65536:
                raise ValueError("Input is empty or too large.")
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict) or not isinstance(body.get("scenario"),dict):
                raise ValueError("Provide water conditions in a scenario object.")
            with self.server.engine_lock:
                frame=self.server.engine.recommend(body["scenario"])
            result={"rows":json.loads(frame.to_json(orient="records")),
                    "summary":frame.attrs["summary"],"profiles":frame.attrs["profile_assessments"]}
            self._send(result)
        except (ValueError,TypeError,KeyError) as error:
            self._send({"error":str(error)},400)
        except Exception:
            self.log_error("Recommendation failed; check the cached project files.")
            self._send({"error":"Could not run the analysis. Check the local model and data files, then try again."},500)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--no-browser",action="store_true")
    args=parser.parse_args()
    try:
        server=LocalServer(("127.0.0.1",args.port))
    except OSError:
        # Reuse a running copy of this app; do not confuse it with another service.
        address=f"http://127.0.0.1:{args.port}/"
        try:
            with urlopen(address+"api/health",timeout=2) as response:
                existing=json.load(response)
            if existing.get("app_id")==APP_ID:
                print(f"NanoSelect is already running: {address}",flush=True)
                if not args.no_browser:
                    webbrowser.open(address)
                return
        except Exception:
            pass
        server=LocalServer(("127.0.0.1",0))
    address=f"http://127.0.0.1:{server.server_port}/"
    print(f"NanoSelect is ready: {address}\nKeep this terminal open. Press Ctrl+C to stop.",flush=True)
    if not args.no_browser:
        threading.Timer(.5,lambda:webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__=="__main__":
    main()
