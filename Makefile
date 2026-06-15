DEV_PORT=8000
NGINX=nginx
GUNICORN=config.wsgi:application

.PHONY: dev stop restart clean check status logs logs-all kill-all health

# ─────────────────────────────
# 🚀 START DEV STACK
# ─────────────────────────────
dev:
	@echo "🧹 Cleaning old processes..."
	@make stop || true

	@test -f .env || (echo "❌ Missing .env file" && exit 1)

	@echo "🚀 Starting Gunicorn (DEV)..."
	@mkdir -p logs
	@set -a; source .env; set +a; \
	gunicorn $(GUNICORN) \
		--bind 127.0.0.1:$(DEV_PORT) \
		--workers 2 \
		--access-logfile logs/gunicorn_access.log \
		--error-logfile logs/gunicorn_error.log \
		--capture-output \
		--log-level info &

	@echo "⏳ Waiting for backend to be ready..."
	@for i in {1..20}; do \
		curl -sf http://127.0.0.1:$(DEV_PORT) > /dev/null && break; \
		echo "waiting..."; \
		sleep 0.5; \
	done

	@echo "🧠 Running health check..."
	@make health || (echo "❌ Backend failed health check. Stopping." && make stop && exit 1)

	@echo "🚀 Starting nginx..."
	@brew services restart $(NGINX)

	@echo "✅ App running at http://localhost:8080"


prod:
	@echo "🚀 Starting PRODUCTION MODE..."
	@ENV=production $(MAKE) dev

# ─────────────────────────────
# 🛑 STOP EVERYTHING (SAFE)
# ─────────────────────────────
stop:
	@echo "Stopping Gunicorn..."
	@pkill -TERM -f gunicorn || true
	@sleep 1
	@pkill -KILL -f gunicorn || true

	@echo "Waiting for port cleanup..."
	@while lsof -i :$(DEV_PORT) >/dev/null 2>&1; do sleep 0.2; done

	@echo "Stopping nginx..."
	@brew services stop $(NGINX) || true


# ─────────────────────────────
# 🧼 EMERGENCY CLEAN (NUCLEAR OPTION)
# ─────────────────────────────
kill-all:
	@echo "💀 Killing Gunicorn..."
	@pkill -f gunicorn || true

	@echo "💀 Killing port $(DEV_PORT)..."
	@lsof -ti :$(DEV_PORT) | xargs kill -9 2>/dev/null || true

	@echo "💀 Stopping nginx..."
	@brew services stop $(NGINX) || true


clean:
	@echo "Cleaning ports + processes..."
	@lsof -ti :$(DEV_PORT) | xargs kill -9 2>/dev/null || true
	@pkill -f gunicorn || true


# ─────────────────────────────
# 🔁 RESTART
# ─────────────────────────────
restart:
	@make stop
	@make dev


# ─────────────────────────────
# ❤️ HEALTH CHECK (BACKEND ONLY)
# ─────────────────────────────
health:

	@echo "=============================="
	@echo "🔍 FULL SYSTEM SNAPSHOT"
	@echo "=============================="

	@echo "🔎 Gunicorn process:"
	@pgrep -f gunicorn > /dev/null && echo "   ✅ running" || echo "   ❌ not running"

	@echo "🔎 Port $(DEV_PORT):"
	@lsof -i :$(DEV_PORT) > /dev/null && echo "   ✅ open" || echo "   ❌ closed"

	@echo "🔎 Django response:"
	@curl -sf http://127.0.0.1:$(DEV_PORT) > /dev/null && echo "   ✅ responding" || echo "   ❌ not responding"

	@echo "🔎 nginx:"
	@brew services list | grep nginx | grep started > /dev/null && echo "   ✅ running" || echo "   ❌ not running"

	@make status

	@echo ""
	@echo "📜 recent gunicorn logs:"
	@tail -n 10 logs/gunicorn_error.log 2>/dev/null || echo "no logs yet"

	@echo ""
	@echo "=============================="

# ─────────────────────────────
# 🔎 STATUS
# ─────────────────────────────
status:
	@echo "🔎 Gunicorn:"
	@pgrep -f gunicorn > /dev/null && echo "✅ running" || echo "❌ not running"

	@echo "🔎 nginx:"
	@brew services list | grep nginx | grep started > /dev/null && echo "✅ running" || echo "❌ not running"

	@echo "🔎 port $(DEV_PORT):"
	@lsof -i :$(DEV_PORT) > /dev/null && echo "✅ in use" || echo "❌ free"

	@echo "🔎 app:"
	@curl -sf http://127.0.0.1:$(DEV_PORT) > /dev/null && echo "✅ responding" || echo "❌ not responding"


# ─────────────────────────────
# 📜 LOGS
# ─────────────────────────────
logs:
	@mkdir -p logs
	@tail -f logs/gunicorn_error.log

logs-all:
	@mkdir -p logs
	@tail -f logs/gunicorn_access.log logs/gunicorn_error.log


# ─────────────────────────────
# 🧪 QUICK CHECK (nginx entrypoint)
# ─────────────────────────────
check:
	@curl -I http://localhost:8080 || echo "App not responding"