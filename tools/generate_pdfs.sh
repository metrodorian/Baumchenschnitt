#!/usr/bin/env bash
# generate_pdfs.sh — Komfort-Wrapper. Die eigentliche Arbeit macht das
# vollständig lokale Python-Skript (kein Live-Deploy nötig).
#
#   ./tools/generate_pdfs.sh
#   git add pdfs/ && git commit -m 'PDFs aktualisiert' && git push
exec python3 "$(dirname "$0")/generate_pdfs.py" "$@"
