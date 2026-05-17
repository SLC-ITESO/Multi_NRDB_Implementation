PYTHON ?= .venv/bin/python
API_HOST ?= 0.0.0.0
API_PORT ?= 8000

.PHONY: services wait-cassandra seed start stop reset

services:
	docker compose up -d

wait-cassandra:
	@echo "Waiting for Cassandra to accept CQL connections..."
	@for i in $$(seq 1 30); do \
		if docker compose exec -T cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES" >/dev/null 2>&1; then \
			echo "Cassandra is ready."; \
			exit 0; \
		fi; \
		echo "Cassandra not ready yet ($$i/30)."; \
		sleep 5; \
	done; \
	echo "Cassandra did not become ready. Check: docker compose logs cassandra"; \
	exit 1

seed:
	$(PYTHON) main.py seed

start: services wait-cassandra seed
	$(PYTHON) -m uvicorn main:app --reload --host $(API_HOST) --port $(API_PORT)

stop:
	docker compose down

reset:
	docker compose down -v
	rm -f .session.json app_events.log
	rm -rf chroma_db
