#!/bin/bash
set -euo pipefail

rm -rf docs/_build/html
sphinx-build -n -W --keep-going -b html docs docs/_build/html
