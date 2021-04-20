# dataclass-opt

[![ci](https://github.com/kmsquire/dataclass-opt/workflows/ci/badge.svg)](https://github.com/kmsquire/dataclass-opt/actions?query=workflow%3Aci)[![documentation](https://img.shields.io/badge/docs-mkdocs%20material-blue.svg?style=flat)](https://kmsquire.github.io/dataclass-opt/)
[![pypi version](https://img.shields.io/pypi/v/dataclass-opt.svg)](https://pypi.org/project/dataclass-opt/)
[![gitter](https://badges.gitter.im/join%20chat.svg)](https://gitter.im/dataclass-opt/community)

Create command line argument parsers using dataclasses

## Requirements

dataclass-opt requires Python 3.7.x or greater.

<details>
<summary>To install Python 3.7, I recommend using <a href="https://github.com/pyenv/pyenv"><code>pyenv</code></a>.</summary>

```bash
# install pyenv
git clone https://github.com/pyenv/pyenv ~/.pyenv

# setup pyenv (you should also put these three lines in .bashrc or similar)
export PATH="${HOME}/.pyenv/bin:${PATH}"
export PYENV_ROOT="${HOME}/.pyenv"
eval "$(pyenv init -)"

# install Python 3.7
pyenv install 3.7.10

# make it available globally
pyenv global system 3.7.10
```

</details>

## Installation

With `pip`:

```bash
python3.7 -m pip install dataclass-opt
```

With [`pipx`](https://github.com/pipxproject/pipx):

```bash
python3.7 -m pip install --user pipx

pipx install --python python3.7 dataclass-opt
```

## Development Setup

Be sure pyenv is installed (see above), then run the following

```bash
git clone https://github.com/kmsquire/dataclass-opt.git
cd dataclass-opt
pyenv local 3.7.10
pip install poetry  # if necessary
make setup
```
