# Sentinel — Infrastructure Monitoring Platform: Operations Manual

## 1. Architecture Overview

Sentinel is a centralized monitoring and alerting platform designed to provide real-time observability across the organization's cloud infrastructure. It aggregates metrics, logs, and traces from all services into a unified dashboard with intelligent alerting.

### Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Metrics Collector | Prometheus + Node Exporter | Scrapes infrastructure and application metrics |
| Log Aggregator | Fluentd → OpenSearch | Collects and indexes structured logs |
| Alert Manager | Prometheus Alertmanager | Evaluates alert rules and routes notifications |
| Dashboard | Grafana | Visualization and real-time monitoring |
| Trace Backend | Jaeger | Distributed tracing for request flow analysis |
| Status Page | Cachet (self-hosted) | Public-facing service status communication |

### Deployment Topology

```
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  App Servers  │     │  Lambda Fns   │     │  Databases   │
  │ (Node Exp.)  │     │ (OTEL SDK)   │     │ (Exporters)  │
  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
         │                    │                     │
         └────────────┬───────┴─────────────────────┘
                      │
              ┌───────▼───────┐
              │   Prometheus   │
              │   (Scraper)    │
              └───────┬───────┘
                      │
           ┌──────────┼──────────┐
           │          │          │
    ┌──────▼──┐  ┌────▼────┐  ┌─▼──────────┐
    │ Grafana  │  │ Alert   │  │ Long-term  │
    │ (Dash)   │  │ Manager │  │ Storage    │
    └──────────┘  └────┬────┘  │ (Thanos)   │
                       │       └────────────┘
              ┌────────▼────────┐
              │  Notification   │
              │  Channels       │
              │ (Slack/PagerDuty│
              │  /Email)        │
              └─────────────────┘
```

---

## 2. Alert Configuration

### Alert Severity Levels

| Level | Response Time | Notification Channel | Escalation |
|-------|--------------|---------------------|------------|
| P1 — Critical | Immediate (< 5 min) | PagerDuty (phone call) | Auto-escalate after 15 min |
| P2 — High | < 30 min | Slack #incidents + PagerDuty | Auto-escalate after 1 hour |
| P3 — Medium | < 4 hours | Slack #alerts | Manual escalation |
| P4 — Low | Next business day | Email digest | No escalation |

### Key Alert Rules

#### CPU Utilization — Sustained High Load
```yaml
# File: alerts/cpu_high.yml
- alert: HighCPUUtilization
  expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
  for: 10m
  labels:
    severity: P2
  annotations:
    summary: "High CPU utilization on {{ $labels.instance }}"
    description: "CPU usage has been above 85% for more than 10 minutes."
    runbook: "https://wiki.internal/sentinel/runbooks/cpu-high"
```

#### Memory Pressure
```yaml
- alert: HighMemoryUsage
  expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90
  for: 5m
  labels:
    severity: P1
  annotations:
    summary: "Critical memory pressure on {{ $labels.instance }}"
    description: "Available memory has dropped below 10% for 5 minutes. OOM killer may activate."
    runbook: "https://wiki.internal/sentinel/runbooks/memory-pressure"
```

#### Disk Space
```yaml
- alert: DiskSpaceLow
  expr: (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes) * 100 > 85
  for: 15m
  labels:
    severity: P2
  annotations:
    summary: "Disk space running low on {{ $labels.instance }} ({{ $labels.mountpoint }})"
    description: "Filesystem usage exceeds 85%. Clean up logs or expand volume."
```

#### Service Downtime
```yaml
- alert: ServiceDown
  expr: up == 0
  for: 2m
  labels:
    severity: P1
  annotations:
    summary: "Service {{ $labels.job }} is down on {{ $labels.instance }}"
    description: "Prometheus has not been able to scrape the target for 2 minutes."
```

---

## 3. Common Troubleshooting

### Prometheus Scrape Failures

**Symptoms:** Grafana dashboards show "No Data" for specific targets. The Prometheus Targets page shows targets in `DOWN` state.

**Root Causes:**
1. **Node Exporter crashed** — The exporter process on the target host is not running.
2. **Network/firewall issue** — Port 9100 (Node Exporter) or 9090 (Prometheus) is blocked.
3. **Scrape timeout** — The target is responding too slowly (default timeout: 10s).

**Resolution Steps:**
1. SSH into the target host and check the exporter:
   ```bash
   sudo systemctl status node_exporter
   sudo systemctl restart node_exporter
   ```
2. Test connectivity from the Prometheus host:
   ```bash
   curl -s http://<target-ip>:9100/metrics | head -20
   ```
3. If the target is slow, increase the scrape timeout in `prometheus.yml`:
   ```yaml
   scrape_configs:
     - job_name: 'slow-target'
       scrape_interval: 30s
       scrape_timeout: 20s
   ```

---

### Alertmanager Not Sending Notifications

**Symptoms:** Alerts are firing in Prometheus (visible in the Alerts tab), but no notifications are received in Slack or PagerDuty.

**Root Causes:**
1. **Alertmanager not connected** — Prometheus is not configured to send alerts to Alertmanager.
2. **Routing mismatch** — The alert labels don't match any route in the Alertmanager config.
3. **Silenced alert** — Someone manually silenced the alert in the Alertmanager UI.

**Resolution Steps:**
1. Verify Prometheus → Alertmanager connectivity:
   ```bash
   curl -s http://localhost:9093/api/v2/status | jq '.cluster'
   ```
2. Check for active silences:
   ```bash
   curl -s http://localhost:9093/api/v2/silences | jq '.[] | select(.status.state=="active")'
   ```
3. Test a notification manually:
   ```bash
   curl -X POST http://localhost:9093/api/v2/alerts \
     -H "Content-Type: application/json" \
     -d '[{"labels":{"alertname":"TestAlert","severity":"P3"},"annotations":{"summary":"Test notification"}}]'
   ```

---

### Grafana Dashboard Loading Slowly

**Symptoms:** Dashboards take more than 10 seconds to load. Some panels show timeout errors.

**Root Causes:**
1. **Expensive PromQL queries** — Queries spanning large time ranges with high cardinality.
2. **Prometheus storage bottleneck** — The TSDB is running on slow storage (e.g., network-attached HDD).
3. **Too many panels** — Dashboards with 50+ panels make too many concurrent queries.

**Resolution Steps:**
1. Use the Prometheus query inspector to identify slow queries:
   - In Grafana, click **Inspect → Query** on the slow panel.
   - Check the `query_duration_seconds` value.
2. Optimize PromQL:
   - Use `rate()` instead of `irate()` for dashboards (smoother, fewer samples).
   - Add label selectors to reduce cardinality: `{job="cortex"}` instead of `{}`.
   - Reduce the time range or increase the step interval.
3. Enable Grafana query caching in `grafana.ini`:
   ```ini
   [caching]
   enabled = true
   ttl = 60
   ```

---

## 4. Incident Response Runbook

### Step 1: Triage (0–5 minutes)

1. **Acknowledge** the alert in PagerDuty/Slack.
2. **Assess severity** — Is this customer-facing? Is data being lost?
3. **Check the status page** — Is there a known ongoing incident?
4. Open the relevant Grafana dashboard for the affected service.

### Step 2: Investigate (5–15 minutes)

1. **Check recent deployments** — Was anything deployed in the last 2 hours?
   ```bash
   git log --oneline --since="2 hours ago" -- deploy/
   ```
2. **Check resource metrics** — CPU, memory, disk, network.
3. **Check application logs** in OpenSearch:
   ```
   service: "cortex-transform" AND level: "ERROR" AND @timestamp > now-1h
   ```
4. **Check distributed traces** in Jaeger for the failing requests.

### Step 3: Mitigate (15–30 minutes)

1. If caused by a bad deployment, **rollback**:
   ```bash
   make rollback STAGE=prod VERSION=<previous-version>
   ```
2. If caused by traffic spike, **scale out**:
   ```bash
   aws lambda put-function-concurrency \
     --function-name cortex-transform-engine \
     --reserved-concurrent-executions 500
   ```
3. If caused by a downstream dependency, **enable circuit breaker** and serve cached/degraded responses.

### Step 4: Resolve and Document (30+ minutes)

1. **Verify recovery** — Confirm metrics have returned to normal.
2. **Update the status page** — Mark the incident as resolved.
3. **Write a postmortem** — Include timeline, root cause, impact, and action items.
4. **Create follow-up tickets** for any identified systemic issues.

---

## 5. Common False Positives

| Alert | False Positive Scenario | Fix |
|-------|------------------------|-----|
| HighCPUUtilization | Scheduled batch job (daily at 03:00 UTC) | Add time-based inhibition rule |
| ServiceDown | Graceful restart during deployment window | Add `for: 5m` to allow restart window |
| DiskSpaceLow | Log rotation hasn't run yet | Ensure logrotate is running: `sudo logrotate -f /etc/logrotate.conf` |
| HighMemoryUsage | JVM garbage collection spike | Increase `for` duration to 10m |
| Scrape Failure | Prometheus itself restarting | Add self-monitoring with a secondary Prometheus instance |

---

## 6. Maintenance Windows

### Scheduled Maintenance

| Day | Time (UTC) | Activity |
|-----|-----------|----------|
| Sunday | 02:00–04:00 | Infrastructure patching and reboots |
| Wednesday | 06:00–07:00 | Database maintenance (vacuum, reindex) |
| 1st of month | 00:00–02:00 | Certificate rotation and secrets renewal |

### How to Schedule a Maintenance Window

1. Create a silence in Alertmanager for the affected services:
   ```bash
   amtool silence add \
     --alertmanager.url=http://localhost:9093 \
     --author="your-name" \
     --comment="Scheduled maintenance" \
     --duration=2h \
     job="cortex"
   ```
2. Update the status page to "Scheduled Maintenance".
3. Notify stakeholders in `#operations` Slack channel.
