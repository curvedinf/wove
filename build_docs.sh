#!/bin/bash
set -euo pipefail

sphinx-build -n -W --keep-going -b html docs docs/_build/html
