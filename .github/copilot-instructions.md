# Copilot Instructions for quri-parts-oqtopus

## Repository Overview

**QURI Parts OQTOPUS** is a Python library that provides a [QURI Parts](https://quri-parts.qunasys.com) backend for executing quantum programs on quantum computers via the [OQTOPUS Cloud](https://github.com/oqtopus-team/oqtopus-cloud) User API.

- Package name: `quri-parts-oqtopus`
- Python: `>=3.10,<3.14`
- Package manager: [uv](https://docs.astral.sh/uv/)
- Build backend: [hatchling](https://hatch.pypa.io/)

## Repository Layout

```
.
├── .github/                  # GitHub configuration (workflows, templates, instructions)
│   ├── instructions/         # Copilot instruction files for commit and PR conventions
│   └── workflows/            # CI/CD workflows (ci.yaml, release.yaml, labeler.yaml)
├── docs/                     # MkDocs documentation source
├── docs_scripts/             # Scripts used during documentation build
├── examples/                 # Usage examples
├── spec/                     # OpenAPI spec and code-generation config for the REST client
├── src/
│   └── quri_parts_oqtopus/   # Main package source
│       ├── backend/          # QURI Parts backend implementation (config, devices, jobs)
│       ├── models/           # Domain model classes (devices, jobs, results)
│       ├── rest/             # Auto-generated REST client (do NOT edit manually)
│       └── sampler.py        # Public sampler entry point
└── tests/
    └── quri_parts_oqtopus/   # Unit tests mirroring src layout
        └── backend/          # Tests for backend modules
```

### Key notes on `src/quri_parts_oqtopus/rest/`

This directory is **auto-generated** from the OQTOPUS Cloud OpenAPI specification using Swagger Codegen. Do **not** edit files here manually. To regenerate:

```bash
cd spec
make download-oas   # fetch latest openapi.yaml from oqtopus-cloud
make generate-api   # regenerate src/quri_parts_oqtopus/rest/
```

Ruff and mypy intentionally exclude `src/quri_parts_oqtopus/rest/` (see `pyproject.toml`).

## Development Workflow

### Setup

```bash
make install        # uv sync --all-groups + configures git commit template
```

### Common commands

| Command | Description |
|---|---|
| `make format` | Auto-fix style issues with ruff |
| `make lint` | Lock-file check, ruff lint+format check, mypy type check |
| `make test` | Run pytest with coverage |
| `make verify` | format + lint + test in one step |
| `make docs-lint` | Lint Markdown files in `docs/` |
| `make docs-build` | Build MkDocs site |
| `make docs-serve` | Serve docs locally |

All commands use `uv run …` internally; you do not need to activate a virtual environment manually.

### CI pipeline

- **lint** job: lock-file check → ruff → mypy → (optional) docs lint
- **test** job (depends on lint): pytest with coverage upload to Codecov
- Triggered on push/PR to `main`.

## Architecture

```
User code (QURI Parts)
    │
    ▼
quri_parts_oqtopus.backend   ← implements QURI Parts Backend/Sampler interfaces
    │  uses
    ▼
quri_parts_oqtopus.models    ← domain objects (Device, Job, Results …)
    │  calls
    ▼
quri_parts_oqtopus.rest      ← auto-generated HTTP client for OQTOPUS Cloud User API
```

- `backend/` contains the concrete QURI Parts backend (`OqtopusBackend`) and job runners (sampling, SSE, estimation).
- `models/` contains Pydantic-style domain models that wrap the raw REST responses.
- `rest/` is never imported directly by user code; it is only used internally by `backend/` and `models/`.

## Code Style

- **Linter / formatter**: [ruff](https://docs.astral.sh/ruff/) — run `make format` to fix, `make lint` to check.
- **Type checker**: [mypy](https://mypy.readthedocs.io/) — strict mode; all public APIs must be typed.
- `tests/` has relaxed ruff rules (no `ANN`, `D`, `S101`, `PLR2004`, etc.).
- Do not add ruff `# noqa` suppression comments without a clear justification.

## Testing

- Framework: **pytest** with `pytest-cov` and `pytest-mock`.
- Run: `make test` (or `uv run pytest`).
- Test files live in `tests/quri_parts_oqtopus/` and mirror the `src/` structure.
- Coverage reports are generated in `htmlcov/` and `coverage.xml`.
- Tests should mock external HTTP calls; no real OQTOPUS Cloud connection is required.

## Known Pitfalls

- The `spec/swagger-codegen-cli-3.0.66.jar` requires Java to be available in `PATH` when regenerating the REST client.
- Documentation linting (`make docs-lint`) only runs in CI when files under `docs/` have changed.
- `uv.lock` must be kept in sync; `make lint` will fail if it is out of date (`uv lock --check`).

## Commit and PR conventions

- Use Conventional Commits style for all commit messages.
- Follow the commit message instructions in `.github/instructions/commit-message.instructions.md`.
- Follow the Pull Request title and description instructions in `.github/instructions/pull-request-description.instructions.md`.
- When creating a Pull Request, follow the sections defined in `.github/pull_request_template.md`.
