#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
coverage run --include=foldbeam/*,tests/* ${DIR}/setup.py test && coverage html
