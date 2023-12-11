## Installation

To install from source:
`pip install .`

For an editable installation during development:
`pip install -e .`


## Development

To install tools for development:
`pip install -e ".[dev]"`

To enable `pre-commit` (included with development tools):
`pre-commit install --install-hooks`

To run `pre-commit` manually:
`pre-commit run`

To apply `pre-commit` to all files:
`pre-commit run --all-files`

To run a specific `pre-commit` check (e.g. `black`):
`pre-commit run black`
