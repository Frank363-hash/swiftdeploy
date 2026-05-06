package canary

import future.keywords.if
import future.keywords.contains

default allow := false

allow if {
    count(deny) == 0
}

deny contains reason if {
    input.error_rate > data.thresholds.max_error_rate
    reason := sprintf(
        "Error rate too high: %.2f%%, maximum is %.2f%%",
        [input.error_rate * 100, data.thresholds.max_error_rate * 100]
    )
}

deny contains reason if {
    input.p99_latency_ms > data.thresholds.max_p99_latency_ms
    reason := sprintf(
        "P99 latency too high: %.0fms, maximum is %dms",
        [input.p99_latency_ms, data.thresholds.max_p99_latency_ms]
    )
}