# Getting Started

This guide gets UnifyRoute running locally with minimal setup.

## Prerequisites

- Python 3.11+
- `uv` (recommended for dependency management)
- Node.js 18+ and npm (for GUI build)
- Redis (local service or Docker)

## Install And Configure

```bash
git clone https://github.com/unifyroute/UnifyRoute.git
cd UnifyRoute
cp sample.env .env
```

Review and update `.env` as needed.

## Setup

```bash
./unifyroute setup
```

This command performs initial install tasks, including dependency sync and database migration.

## Start Services

```bash
./unifyroute start
```

Default URLs:

- Dashboard/API root: `http://localhost:6565`
- OpenAI-compatible base: `http://localhost:6565/api/v1`

## Optional Wizard

```bash
./unifyroute wizard
```

Use this after setup to configure providers and routing interactively.

## Verify

```bash
curl http://localhost:6565/api/v1/models
```

## Windows Git Bash Notes

If `./unifyroute` fails due to Python command resolution:

```bash
python --version
# or
py --version
```

The launcher probes `python`, then `python3`, then `py -3`.
