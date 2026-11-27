#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Create .venv and install local_review/requirements.txt using the README first.' >&2
  exit 2
fi
exec .venv/bin/python -m local_review.server "$@"
