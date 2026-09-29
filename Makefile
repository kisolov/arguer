.PHONY: build up down restart log ps debug db-volume-purge

build:
	docker-compose build $(c)

up:
	docker-compose up -d $(c)

down:
	docker-compose down $(c)

restart: down up

log:
	docker-compose logs -f $(c)

db-volume-purge:
	docker volume rm arguer_mysql_data

ps:
	docker-compose ps $(c)
