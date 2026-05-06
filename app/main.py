import os
import time
import random
import threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify, Response
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
    REGISTRY
)

app = Flask(__name__)

MODE        = os.environ.get("MODE", "stable")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
APP_PORT    = int(os.environ.get("APP_PORT", 3000))
START_TIME  = time.time()

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

app_uptime_seconds = Gauge(
    "app_uptime_seconds",
    "Application uptime in seconds"
)

app_mode_gauge = Gauge(
    "app_mode",
    "Current app mode: 0=stable, 1=canary"
)

chaos_active_gauge = Gauge(
    "chaos_active",
    "Current chaos state: 0=none, 1=slow, 2=error"
)

app_mode_gauge.set(1 if MODE == "canary" else 0)
chaos_active_gauge.set(0)

chaos_state = {
    "mode": None,
    "duration": 0,
    "rate": 0.0,
}
chaos_lock = threading.Lock()


@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def track_metrics(response):
    if request.path == "/metrics":
        return response

    duration = time.time() - getattr(request, "_start_time", time.time())
    http_requests_total.labels(
        method=request.method,
        path=request.path,
        status_code=str(response.status_code)
    ).inc()
    http_request_duration_seconds.labels(
        method=request.method,
        path=request.path
    ).observe(duration)
    return response


def make_response(data, status=200):
    resp = jsonify(data)
    resp.status_code = status
    if MODE == "canary":
        resp.headers["X-Mode"] = "canary"
    return resp

def apply_chaos():
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
    app_uptime_seconds.set(uptime)
    return make_response({
        "status": "ok",
        "uptime_seconds": uptime,
    })


@app.route("/metrics")
def metrics():
    app_uptime_seconds.set(round(time.time() - START_TIME, 2))
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


@app.route("/chaos", methods=["POST"])
def chaos():
    if MODE != "canary":
        return make_response(
            {"error": "chaos endpoint only available in canary mode"}, 403
        )

    body = request.get_json(silent=True) or {}
    mode = body.get("mode")

    with chaos_lock:
        if mode == "slow":
            chaos_state["mode"]     = "slow"
            chaos_state["duration"] = int(body.get("duration", 1))
            chaos_active_gauge.set(1)
            msg = f"Chaos: slow mode active for {chaos_state['duration']}s"

        elif mode == "error":
            chaos_state["mode"] = "error"
            chaos_state["rate"] = float(body.get("rate", 0.5))
            chaos_active_gauge.set(2)
            msg = f"Chaos: error mode active at {chaos_state['rate']*100}% rate"

        elif mode == "recover":
            chaos_state["mode"]     = None
            chaos_state["duration"] = 0
            chaos_state["rate"]     = 0.0
            chaos_active_gauge.set(0)
            msg = "Chaos: recovered, all systems normal"

        else:
            return make_response(
                {"error": "invalid chaos mode. use: slow, error, recover"}, 400
            )

    return make_response({"message": msg, "chaos_mode": mode})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)