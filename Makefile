.PHONY: up stop prune ps logs-all logs

up:
	docker compose up --build -d

stop:
	docker compose stop
	docker compose down

prune:
	docker system prune -a -f

ps:
	docker ps

logs-all:
	docker compose logs -f

logs:
ifndef container
	$(error Необходимо указать имя контейнера, например: make logs container=app)
endif
	docker compose logs -f $(container)
