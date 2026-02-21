.PHONY: all setup build run clean omni omni-status omni-logs omni-stop

all: setup build run

# 🚀 Omnibus deployment - Run ALL systems
omni:
	@echo "🚀 Starting Omnibus Deployment..."
	./run-all-omni.sh

# Check status of all omnibus services
omni-status:
	@echo "📊 Omnibus Service Status:"
	@docker-compose ps
	@echo ""
	@echo "📈 System Resources:"
	@docker stats --no-stream

# View logs from all omnibus services
omni-logs:
	@echo "📝 Omnibus Service Logs:"
	docker-compose logs -f --tail=100

# Stop all omnibus services
omni-stop:
	@echo "🛑 Stopping Omnibus Services..."
	docker-compose down
	@echo "✅ All omnibus services stopped"

setup:
	@echo "📦 Initializing Ecosystem..."
	git submodule update --init --recursive
	@echo "✅ Submodules synced"

build:
	@echo "🏗️  Building All Systems..."
	docker-compose build
	@echo "✅ Build complete"

run:
	@echo "🚀 Launching Ecosystem..."
	docker-compose up -d
	@echo "✅ All systems running"
	@echo "📊 Dashboard: http://localhost:8080"
	@echo "🌐 Portfolio: http://localhost:80"

stop:
	@echo "🛑 Stopping Ecosystem..."
	docker-compose down

clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	git submodule foreach git clean -fdx
