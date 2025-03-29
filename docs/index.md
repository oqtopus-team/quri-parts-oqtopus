![OQTOPUS logo](./asset/oqtopus-logo.png)

# QURI Parts OQTOPUS

[![CI](https://github.com/oqtopus-team/quri-parts-oqtopus/actions/workflows/ci.yaml/badge.svg)](https://github.com/oqtopus-team/quri-parts-oqtopus/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/oqtopus-team/quri-parts-oqtopus/graph/badge.svg?token=RCXTMMXOMV)](https://codecov.io/gh/oqtopus-team/quri-parts-oqtopus)
[![pypi version](https://img.shields.io/pypi/v/quri-parts-oqtopus.svg)](https://pypi.org/project/quri-parts-oqtopus/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![slack](https://img.shields.io/badge/slack-OQTOPUS-pink.svg?logo=slack&style=plastic")](https://oqtopus.slack.com/archives/C08K2QQ30UA)

## Overview

**QURI Parts OQTOPUS** is a library that allows QURI Parts users to run quantum computers using OQTOPUS Cloud.

- **Provides a Backend for QURI Parts**: QURI Parts users can execute quantum programs on quantum computers in OQTOPUS Cloud using the backend provided by QURI Parts OQTOPUS.
- **Utilizes the User API of OQTOPUS Cloud**: QURI Parts OQTOPUS executes quantum programs via the User API of OQTOPUS Cloud and handles communication with the cloud. This allows users to run quantum computers without having to be aware of the communication protocols of OQTOPUS Cloud.

![QURI Parts OQTOPUS](./asset/overview.png)

## Features

- **Sampling Job**: Samples quantum circuits.
- **Multiprogramming Job** (Planned): Combines multiple sampling jobs into a single quantum circuit and executes them simultaneously.
- **Expectation Value Job** (Planned): Computes expectation values using quantum circuits.
- **SSE (Server Side Execution) Job** (Planned): Runs Python programs on the server instead of the user’s PC, exclusively using the quantum computer. This enables fast execution of hybrid classical-quantum algorithms such as QAOA.

## Usage

- [Getting Started](./usage/getting_started.ipynb)
- [QURI Parts Documentation](https://quri-parts.qunasys.com)
- [QURI Parts OQTOPUS Examples](https://github.com/oqtopus-team/quri-parts-oqtopus/tree/main/examples)

## API reference

- [API reference](./reference/API_reference.md)

## Developer Guidelines

- [Development Flow](./developer_guidelines/index.md)
- [Setup Development Environment](./developer_guidelines/setup.md)
- [How to Contribute](./CONTRIBUTING.md)
- [Code of Conduct](https://oqtopus-team.github.io/code-of-conduct/)
- [Security](https://oqtopus-team.github.io/security-policy/)

## Citation

You can use the DOI to cite QURI Parts OQTOPUS in your research.

[![DOI](https://zenodo.org/badge/943222082.svg)](https://zenodo.org/badge/latestdoi/943222082)

Citation information is also available in the [CITATION](https://github.com/oqtopus-team/quri-parts-oqtopus/blob/main/CITATION.cff) file.

## Contact

You can contact us by creating an issue in this repository or by email:

- [oqtopus-team[at]googlegroups.com](mailto:oqtopus-team[at]googlegroups.com)

## License

Tranqu is released under the [Apache License 2.0](https://github.com/oqtopus-team/quri-parts-oqtopus/blob/main/LICENSE).

## Supporting

This work was supported by JST COI-NEXT, Grant No. JPMJPF2014.
