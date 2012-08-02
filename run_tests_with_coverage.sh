#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
coverage run --omit=*.local*,*tests/*,setup ${DIR}/setup.py test && coverage html
