# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Phase-4 Spec-Parity Fixes

#### Added
- Memory limits to docker-compose files (1.5GB per service)
- Implemented guard systems:
  - ModeGuard: Monitors mode transitions and pauses trading after 3 HV→LV transitions in 15 minutes
  - KillSwitch: Monitors daily loss and suspends trading for 24 hours when loss exceeds -1.5%
  - LatencyGuard: Monitors API latency and fails safe to LV-LL mode after 5 consecutive high latencies
  - PriorityGuard: Manages bot priority and resource allocation
- Added pytest markers (unit, integration, sim) for test categorization
- Implemented SIM Refresh-Token 24h validity check
- Added SIM canary tests for both bots with required KPIs:
  - Fill Rate ≥ 92%
  - Profit Factor ≥ 0.9
  - Latency ≤ 250 ms
- Added integration tests for all guard systems

#### Changed
- Moved SlippageGuard to new guards module
- Updated test files with appropriate markers
- Updated WBS.md with completed tasks

#### Fixed
- Ensured CPU pinning configuration matches specification
- Verified no hard-coded secrets in configuration files
