import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from inference.predictor import Predictor
from sessions.decoder import DecoderSession
from sessions.practice import PracticeSession
from sessions.hangman import HangmanSession

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT.parent / "frontend"
MODEL_PATH = ROOT / "models" / "asl.pt"

app = FastAPI(title="SignSpeak")
predictor = Predictor(MODEL_PATH)


@app.get("/api/status")
async def status():
    return {"ok": True, "model_loaded": predictor.is_loaded}


@app.middleware("http")
async def reference_asset_cache_control(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/assets/reference/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


async def _run_session(ws: WebSocket, session):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                result = session.process_frame(msg["bytes"])
                await ws.send_json(result)
            elif msg.get("text") is not None:
                try:
                    control = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                result = session.handle_control(control)
                if result is not None:
                    await ws.send_json(result)
    except WebSocketDisconnect:
        pass
    finally:
        session.close()


@app.websocket("/ws/decoder")
async def ws_decoder(ws: WebSocket):
    await _run_session(ws, DecoderSession(predictor))


@app.websocket("/ws/practice")
async def ws_practice(ws: WebSocket):
    await _run_session(ws, PracticeSession(predictor))


@app.websocket("/ws/hangman")
async def ws_hangman(ws: WebSocket):
    await _run_session(ws, HangmanSession(predictor))


# Serve built static assets; unknown paths fall back to index.html for SPA routing.
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
async def spa_root():
    index = FRONTEND_DIR / "index.html"
    return FileResponse(index)


@app.get("/{full_path:path}")
async def spa(full_path: str):
    candidate = FRONTEND_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    index = FRONTEND_DIR / "index.html"
    return FileResponse(index)
