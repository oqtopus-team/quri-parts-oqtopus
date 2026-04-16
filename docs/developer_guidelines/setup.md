
# Development Environment Setup

## Prerequisites

Install the following tools before starting development.

| Tool                                        | Version  | Description                        |
|---------------------------------------------|----------|------------------------------------|
| [Python](https://www.python.org/downloads/) | >=3.10   | Python programming language        |
| [uv](https://docs.astral.sh/uv/)            | -        | Python package and project manager |
| [Java](https://openjdk.org/)                | >=21.0.0 | Java programming language          |

To start development, clone the repository:

```shell
git clone https://github.com/oqtopus-team/quri-parts-oqtopus.git
cd quri-parts-oqtopus
```

## Project Structure

The repository is organized as follows:

```text
python-project-template/
├─ src/           # Python package source code
├─ tests/         # Test suite
├─ docs/          # Documentation sources (MkDocs)
├─ config/        # Example configuration files (optional)
├─ .vscode/       # VSCode settings (optional)
├─ .github/       # GitHub workflows and repository settings
├─ pyproject.toml # Project configuration and dependencies
├─ Makefile       # Development commands
├─ mkdocs.yml     # MkDocs configuration
├─ uv.lock        # Locked dependency versions
└─ README.md      # Project overview
```

## Installing Dependencies

### Setting Up the Python Environment

Install the project dependencies and set up the local development environment:

```shell
make install
```

This command performs the following:

- Installs all dependencies via `uv`.
- Configures the Git commit message template.

### Setting Up the Java(JDK) Environment

To use `swagger-codegen-cli` to generate Python code from an OQTOPUS Cloud User API definition, install JDK:

```shell
sudo apt install -y openjdk-21-jdk
```

## Download the OQTOPUS Cloud User API definition

To download the OQTOPUS Cloud User API definition, run the following command in the `spec` directory:

```shell
make download-oas
```

## Generate Python code

To generate Python code, run the following command in the `spec` directory:

```shell
make generate-api
```

## Linting and Testing

### Format Code

Format the code:

```shell
make format
```

### Lint Code

Run linting and static type checking:

```shell
make lint
```

### Run Tests

Run the test suite:

```shell
make test
```

### Verify Code

Run all verification steps (formatting, linting, and tests):

```shell
make verify
```

## Documentation

### Lint Documentation

Run documentation linting:

```shell
make docs-lint
```

### Build Documentation

Build the documentation:

```shell
make docs-build
```

### Start the Documentation Server

This project uses [MkDocs](https://www.mkdocs.org/) to generate the HTML documentation and
[mkdocstrings-python](https://mkdocstrings.github.io/python/) to generate the Python API reference.  
Start the documentation server with:

```shell
make docs-serve
```

Open the documentation in your browser at [http://localhost:8000](http://localhost:8000).