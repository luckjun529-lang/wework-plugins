#!/bin/sh

set -eu

DWS_SCRIPT_DIRECTORY="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec /bin/sh "${DWS_SCRIPT_DIRECTORY}/run-python.sh" "${DWS_SCRIPT_DIRECTORY}/dws.py" "$@"
