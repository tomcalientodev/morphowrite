#!/bin/bash

echo "Killing anything on port 8000..."

lsof -ti :8000 | xargs kill -9 2>/dev/null || true

echo "Killing Gunicorn processes (backup safety)..."
pkill -f gunicorn 2>/dev/null || true

echo "Done."
