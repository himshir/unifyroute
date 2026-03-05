# CLI Reference

The project ships with the `./unifyroute` command.

## Core Commands

```bash
./unifyroute setup
./unifyroute setup refresh
./unifyroute setup uninstall

./unifyroute start
./unifyroute stop
./unifyroute restart

./unifyroute wizard
```

## Token Management

```bash
./unifyroute get token [all|admin|api]
./unifyroute create token [admin|api]
./unifyroute update token <id> <label>
```

## Credential Operations

```bash
./unifyroute import-keys <file.json>
```

## Help

```bash
./unifyroute help
```

## Typical Workflow

```bash
./unifyroute setup
./unifyroute wizard
./unifyroute start
./unifyroute get token
```
