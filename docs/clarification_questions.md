# Clarification Questions

## General Questions

1. **GitHub Repository Setup**: Should the repository be created as a public or private repository? The current implementation assumes it will be hosted at `ikoma30/saxo-bot`.

2. **Deployment Strategy**: The specifications mention deployment to a VPS at `/opt/saxo-bot/`. Is there a specific deployment workflow or script that should be implemented beyond the `oneclick_start.sh` script?

3. **Authentication Flow**: The specifications mention OAuth2 PKCE flow for token rotation. Is there a specific implementation or library that should be used for this?

## Technical Questions

1. **Feature Implementation Priority**: Given the extensive feature set described in the specifications, is there a priority order for implementing features beyond the phase plan?

2. **Testing Strategy**: The specifications mention test coverage requirements (≥85% lines / ≥70% branches). Are there specific test scenarios or edge cases that should be prioritized?

3. **Model Training**: The Main BOT specification mentions nightly retraining if KS-stat > 0.15. Is there a specific implementation or algorithm for calculating KS-stat?

4. **Monitoring Stack**: The specifications mention Prometheus, Grafana, and Alertmanager. Are there specific dashboards or alert configurations that should be implemented?

## Integration Questions

1. **External Systems**: The specifications mention integration with Backblaze B2 bucket for MLflow artifacts. Are there any other external systems that need to be integrated?

2. **API Versioning**: The specifications mention using environment variable USE_TRADE_V3 to switch between v2/v3 Trade API. Are there any specific differences or considerations when implementing support for both versions?

3. **News Feed Providers**: The specifications mention forex_factory_ics, gov_bls, and stub_json as news feed providers. Are there any specific implementation details or considerations for these providers?

## Operational Questions

1. **Backup and Recovery**: The specifications mention backup to Wasabi ObjStorage for tick data. Are there any specific backup and recovery procedures that should be implemented?

2. **Monitoring and Alerting**: The specifications mention Slack alerts and OpsGenie fallback. Are there any specific alert thresholds or conditions that should be implemented beyond what's specified?

3. **Chaos Drill**: The specifications mention monthly chaos drills. Is there a specific schedule or procedure for these drills?
