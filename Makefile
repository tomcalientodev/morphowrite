DEV_PORT=8000
NGINX=nginx
GUNICORN=config.wsgi:application

dev:
	@echo "Stopping existing services..."
	@lsof -ti :$(DEV_PORT) | xargs kill -9 2>/dev/null || true
	@pkill -f gunicorn 2>/dev/null || true

	@mkdir -p logs

	@echo "Starting Gunicorn..."
	@gunicorn $(GUNICORN) \
		--bind 127.0.0.1:$(DEV_PORT) \
		--workers 2 \
		--access-logfile logs/gunicorn_access.log \
		--error-logfile logs/gunicorn_error.log &

	@echo "Starting nginx..."
	@brew services restart $(NGINX)

	@echo "Done -> http://localhost:8080"

stop:
	@echo "Stopping Gunicorn..."
	@lsof -ti :$(DEV_PORT) | xargs kill -9 2>/dev/null || true
	@pkill -f gunicorn 2>/dev/null || true

	@echo "Stopping nginx..."
	@brew services stop $(NGINX)

	@echo "Stopped cleanly"
