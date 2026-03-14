#!/bin/bash

echo "=== Safedep Security Scan ==="
REQ_FILE="backend/requirements.txt"
REPORT_FILE="safedep_report.json"

if command -v safedep &> /dev/null; then
    safedep scan --file "$REQ_FILE" --format table || true
    safedep scan --file "$REQ_FILE" --format json > "$REPORT_FILE" || true
    echo "Report saved to $REPORT_FILE"
elif command -v docker &> /dev/null; then
    docker run --rm -v "$(pwd)":/app safedep/cli scan --file "/app/$REQ_FILE" || true
    docker run --rm -v "$(pwd)":/app safedep/cli scan --file "/app/$REQ_FILE" --format json > "$REPORT_FILE" || true
    echo "Report saved to $REPORT_FILE"
elif [ -x "/app/bin/vet" ]; then
    /app/bin/vet scan -M "/app/$REQ_FILE" --report-console --report-json "/app/$REPORT_FILE" || true
    echo "Report saved to $REPORT_FILE"
else
    echo "SafeDep scanner unavailable: install safedep, docker, or /app/bin/vet"
fi
