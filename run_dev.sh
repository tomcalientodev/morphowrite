#!/bin/bash

echo "Ensuring clean state first..."
./stop_dev.sh

sleep 1

if lsof -i :8000 >/dev/null; then
  echo "Port 8000 still in use. Aborting."
  exit 1
fi

echo "Starting Gunicorn..."
gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers 2 \
  --access-logfile - \
  --error-logfile - &

echo "Ensuring nginx is running..."
brew services restart nginx >/dev/null

echo "Done"
echo "App: http://localhost:8080"