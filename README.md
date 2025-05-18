# Saxo Bot

Automated trading system for Saxo Bank's OpenAPI, implementing dual-bot strategy with risk management.

## Overview

This system implements:
- **Parent Orchestrator**: Risk guard and API management (v1.2.14)
- **Main BOT**: AI-EdgeEnsemble for primary trading (v7.4.15)
- **Micro-Rev BOT**: Event-driven trading strategy (v1.3.15)

## Features

- OAuth2 authentication with token rotation
- Live and simulation environment support
- Prometheus/Grafana monitoring with alerts
- CPU pinning for optimal performance
- MLflow integration with Backblaze B2 storage
- News feed integration for economic events

## Installation

```bash
# Clone the repository
git clone https://github.com/ikoma30/saxo-bot.git
cd saxo-bot

# Install dependencies
poetry install

# Set up environment variables
cp .env.sample .env.sim  # For simulation environment
cp .env.sample .env.live  # For live environment
# Edit .env files with your API credentials
```

## Usage

```bash
# Start in simulation mode
sudo ./scripts/oneclick_start.sh sim

# Start in live mode
sudo ./scripts/oneclick_start.sh live
```

## Project Structure

- `src/core/`: Core functionality (SaxoClient, RiskGuard, Orchestrator)
- `src/services/`: Main BOT and Micro-Rev BOT implementations
- `src/common/`: Shared utilities and configurations
- `docker/`: Docker compose files for deployment
- `scripts/`: Utility scripts including oneclick_start.sh
- `tests/`: Unit and integration tests

## Development

```bash
# Run tests
poetry run pytest

# Lint code
poetry run ruff check .
poetry run black .
poetry run mypy .
```

## License

Proprietary - All rights reserved
