import os
import time
import random
import threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

MODE        = os.environ.get("MODE", "stable")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
APP_PORT    = int(os.environ.get("APP_PORT", 3000))

START_TIME  = time.time()

chaos_state = {
    "mode": None,       # "slow" | "error" | None
    "duration": 0,      # seconds to sleep (slow mode)
    "rate": 0.0,        # error rate (error mode)
}
chaos_lock = threading.Lock()

def make_response(data, status=200):
    resp = jsonify(data)
    resp.status_code = status
    if MODE == "canary":
        resp.headers["X-Mode"] = "canary"
    return resp

def apply_chaos():
    """Returns an error response if chaos is active, else None."""
    with chaos_lock:
        c = chaos_state.copy()

    if c["mode"] == "slow":
        time.sleep(c["duration"])

    elif c["mode"] == "error":
        if random.random() < c["rate"]:
            return make_response({"error": "chaos error injection"}, 500)

    return None

@app.route("/")
def index():
    chaos_resp = apply_chaos()
    if chaos_resp:
        return chaos_resp

    return make_response({
        "message": f"Welcome to SwiftDeploy! Running in {MODE} mode.",
        "mode":      MODE,
        "version":   APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

@app.route("/healthz")
def healthz():
    uptime = round(time.time() - START_TIME, 2)
    return make_response({
        "status": "ok",
        "uptime_seconds": uptime,
    })

@app.route("/chaos", methods=["POST"])
def chaos():
    # Only available in canary mode
    if MODE != "canary":
        return make_response({"error": "chaos endpoint only available in canary mode"}, 403)

    body = request.get_json(silent=True) or {}
    mode = body.get("mode")

    with chaos_lock:
        if mode == "slow":
            chaos_state["mode"]     = "slow"
            chaos_state["duration"] = int(body.get("duration", 1))
            msg = f"Chaos: slow mode active for {chaos_state['duration']}s"

        elif mode == "error":
            chaos_state["mode"] = "error"
            chaos_state["rate"] = float(body.get("rate", 0.5))
            msg = f"Chaos: error mode active at {chaos_state['rate']*100}% rate"

        elif mode == "recover":
            chaos_state["mode"]     = None
            chaos_state["duration"] = 0
            chaos_state["rate"]     = 0.0
            msg = "Chaos: recovered, all systems normal"

        else:
            return make_response({"error": "invalid chaos mode. use: slow, error, recover"}, 400)

    return make_response({"message": msg, "chaos_mode": mode})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)