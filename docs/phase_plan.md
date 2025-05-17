# Development Phases (Waterfall)

| Phase | Owner | Milestone (Done = ✓) | Description |
|-------|-------|----------------------|-------------|
| 0 – Infra / Auth Prep | _me_ |  | VPS setup, Git init, Secrets |
| 1 – Devin Prompt | _me_ |  | Attach specs & prompt |
| 2 – Spec parsing & WBS | Devin |  | Generate tasks, push dirs |
| 3 – Impl & Unit Test | Devin |  | pytest --cov≥85 % green |
| 4 – Integration Test (Sim) | Devin CI |  | 30 s healthz, canary trades |
| 5 – Live Canary | Devin CI |  | 2 h smoke, PF ≥0.9 |
| 6 – Auto-deploy & Release | Devin |  | cosign sign, GH Release |
| 7 – Production start | _me_ |  | oneclick_start.sh live |
| 8 – Ops & Improvement | auto + _me_ |  | nightly backtest, KPI drift |
