#!/bin/bash
# Run tests inside the API container

echo "🧪 Running tests..."
docker compose exec api pytest tests/ -v

echo ""
echo "Test run completed!"
