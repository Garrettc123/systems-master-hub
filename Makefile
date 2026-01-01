.PHONY: all setup build run clean

all: setup build run

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
