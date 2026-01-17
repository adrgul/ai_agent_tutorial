.PHONY: help build run clean

help:
	@echo "AI Chat Console - Parancsok:"
	@echo ""
	@echo "  make run     - Chat indítása (interaktív mód)"
	@echo "  make build   - Docker image build"
	@echo "  make clean   - Konténerek törlése"
	@echo "  make local   - Lokális futtatás (Python)"
	@echo ""

build:
	@echo "Docker image build..."
	docker-compose build

run:
	@echo "Chat indítása interaktív módban..."
	@echo "Kilépés: 'exit' vagy Ctrl+D"
	@echo ""
	docker-compose run --rm chat

clean:
	@echo "Konténerek törlése..."
	docker-compose down
	docker rmi ai-chat-console 2>/dev/null || true

local:
	@echo "Lokális futtatás..."
	python chat.py

