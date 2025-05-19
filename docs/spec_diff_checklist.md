# Specification Diff Checklist

This document compares the implementation against the three specification documents:
- Parent Guard v1.2.14
- Main BOT v7.4.15
- Micro-Rev BOT v1.3.15

## Parent Guard Specification v1.2.14

| ID | Requirement | Implementation | Status |
|----|-------------|----------------|--------|
| RG-01 | MU Soft threshold 60% | Implemented in config | ✅ |
| RG-02 | MU Hard threshold 90% | Implemented in config | ✅ |
| RG-03 | Daily DD threshold -1.5% | Implemented in KillSwitch | ✅ |
| RG-04 | Environment variable USE_TRADE_V3 | Implemented in SaxoClient | ✅ |
| RG-05 | Rate limit backoff | Implemented in retryable decorator | ✅ |
| RG-06 | Fallback alert notification | Implemented in verify_monitoring.py | ✅ |
| RG-07 | Bot priority (Micro-Rev HIGH, Main NORMAL) | Implemented in PriorityGuard | ✅ |

## Main BOT Specification v7.4.15

| ID | Requirement | Implementation | Status |
|----|-------------|----------------|--------|
| UT-M-01 | ATR-Band calculation | Implemented in tests | ✅ |
| UT-M-05 | LatencyGuard judgment (5 consecutive RTDs > 12ms) | Implemented in LatencyGuard | ✅ |
| UT-M-07 | Mode downgrade on latency | Implemented | ✅ |
| UT-M-08 | Priority Guard (Main paused when Micro-Rev running) | Implemented in PriorityGuard | ✅ |
| UT-M-09 | Rate limit backoff | Implemented | ✅ |
| UT-M-10 | V3 DTO mapping | Implemented with USE_TRADE_V3 | ✅ |
| IT-KPI-01 | Fill rate >= 92% | Implemented in canary tests | ✅ |
| IT-KPI-02 | Latency guard trigger 0 times | Implemented in tests | ✅ |

## Micro-Rev BOT Specification v1.3.15

| ID | Requirement | Implementation | Status |
|----|-------------|----------------|--------|
| IT-KPI-01 | Fill rate >= 92% | Implemented in canary tests | ✅ |
| IT-KPI-02 | Slippage guard trigger 0 times | Implemented in tests | ✅ |
| IT-KPI-03 | Trade latency p95 <= 250ms | Implemented in tests | ✅ |
| OT-R-01 | Kill switch DD -1.5% | Implemented in KillSwitch | ✅ |
| OT-R-02 | Slippage guard trigger | Implemented in SlippageGuard | ✅ |
| OT-R-03 | Blocking disclaimer handling | Implemented in SaxoClient | ✅ |

## Implemented Fixes

1. ✅ Updated KillSwitch daily loss threshold to -1.5%
2. ✅ Updated LatencyGuard threshold to 12ms
3. ✅ Implemented storage of canary test results in JSON format
4. ✅ Implemented generation of HTML trade reports
5. ✅ Implemented export of Prometheus metrics
6. ✅ Implemented fallback alert notification (RG-06)

## Canary Test KPIs

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Fill Rate | ≥ 92% | TBD | TBD |
| Performance Factor | ≥ 0.9 | TBD | TBD |
| Latency | ≤ 250 ms | TBD | TBD |

## Test Coverage

| Module | Line Coverage | Branch Coverage | Status |
|--------|--------------|----------------|--------|
| Overall | ≥ 85% | ≥ 70% | TBD |
| Core | TBD | TBD | TBD |
| Guards | TBD | TBD | TBD |
| API | TBD | TBD | TBD |

## Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| Canary Test Results | reports/canary_*_YYYYMMDD_HHMMSS.json | Raw JSON data of canary test results |
| Trade Report | reports/saxo_trades_*.html | HTML report of trades with download link |
| Prometheus Metrics | reports/prometheus_metrics_*.json | Exported metrics from Prometheus |
