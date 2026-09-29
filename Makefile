.PHONY: build up up-dev down restart log ps db-volume-purge

build:
	docker-compose build $(c)

up:
	docker-compose up -d $(c)

up-dev:
	docker-compose --profile dev up -d $(c)

down:
	docker-compose down $(c)

restart: down up

log:
	docker-compose logs -f $(c)

db-volume-purge:
	docker volume rm arguer_mysql_data

ps:
	docker-compose ps $(c)
