.PHONY: all setup build run clean omni omni-status omni-logs omni-stop

# Docker Compose command (supports both v1 and v2)
DOCKER_COMPOSE := $(shell command -v docker-compose 2> /dev/null || echo "docker compose")

all: setup build run

# 🚀 Omnibus deployment - Run ALL systems
omni:
	@echo "🚀 Starting Omnibus Deployment..."
	./run-all-omni.sh

# Check status of all omnibus services
omni-status:
	@echo "📊 Omnibus Service Status:"
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "📈 System Resources:"
	@docker stats --no-stream

# View logs from all omnibus services
omni-logs:
	@echo "📝 Omnibus Service Logs:"
	$(DOCKER_COMPOSE) logs -f --tail=100

# Stop all omnibus services
omni-stop:
	@echo "🛑 Stopping Omnibus Services..."
	$(DOCKER_COMPOSE) down
	@echo "✅ All omnibus services stopped"

setup:
	@echo "📦 Initializing Ecosystem..."
	git submodule update --init --recursive
	@echo "✅ Submodules synced"

build:
	@echo "🏗️  Building All Systems..."
	$(DOCKER_COMPOSE) build
	@echo "✅ Build complete"

run:
	@echo "🚀 Launching Ecosystem..."
	$(DOCKER_COMPOSE) up -d
	@echo "✅ All systems running"
	@echo "📊 Dashboard: http://localhost:8080"
	@echo "🌐 Portfolio: http://localhost:80"

stop:
	@echo "🛑 Stopping Ecosystem..."
	$(DOCKER_COMPOSE) down

clean:
	@echo "🧹 Cleaning up..."
	$(DOCKER_COMPOSE) down -v
	git submodule foreach git clean -fdx
