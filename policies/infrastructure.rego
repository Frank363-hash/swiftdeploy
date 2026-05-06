package infrastructure

import future.keywords.if
import future.keywords.contains

default allow := false

allow if {
    count(deny) == 0
}

deny contains reason if {
    input.disk_free_gb < data.thresholds.min_disk_gb
    reason := sprintf(
        "Disk space too low: %.1fGB free, minimum is %dGB",
        [input.disk_free_gb, data.thresholds.min_disk_gb]
    )
}

deny contains reason if {
    input.cpu_load > data.thresholds.max_cpu_load
    reason := sprintf(
        "CPU load too high: %.2f, maximum is %.1f",
        [input.cpu_load, data.thresholds.max_cpu_load]
    )
}