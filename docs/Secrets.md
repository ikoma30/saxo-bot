| Secret name            | Scope  | Purpose / API | Rotation policy | Notes |
|------------------------|--------|---------------|-----------------|-------|
| LIVE_CLIENT_ID         | Live   | OAuth2 PKCE   | static          | Obtain from Saxo dev-portal |
| LIVE_CLIENT_SECRET     | Live   | OAuth2 PKCE   | yearly manual   | — |
| LIVE_REFRESH_TOKEN     | Live   | OAuth2        | weekly via GH Action | auto-rotated |
| LIVE_ACCOUNT_KEY       | Live   | Account ID    | static          | — |
| SIM_CLIENT_ID          | Sim    | OAuth2 PKCE   | static          | — |
| SIM_CLIENT_SECRET      | Sim    | OAuth2 PKCE   | yearly manual   | — |
| SIM_REFRESH_TOKEN      | Sim    | OAuth2        | weekly via GH Action | auto-rotated |
| SIM_ACCOUNT_KEY        | Sim    | Account ID    | static          | — |
| REFINITIV_API_KEY      | Both   | News feed     | yearly manual   | Parent §5.7 |
| ICE_FX_API_KEY         | Both   | News feed backup | yearly manual | — |
| MLFLOW_S3_KEY          | Both   | MLflow S3     | half-yearly     | Parent §4.14 |
| MLFLOW_S3_SECRET       | Both   | MLflow S3     | half-yearly     | — |
| SLACK_WEBHOOK          | Both   | Alerting      | static          | — |
| OG_GENIE_KEY           | Both   | OpsGenie      | static          | — |
