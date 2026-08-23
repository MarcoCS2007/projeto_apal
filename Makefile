.PHONY: up migrate makemigrations createsuperuser precommit test bash

up:
	docker compose up --build

up-prod:
	docker compose -f docker-compose.prod.yml --env-file .envs/.env.prod up -d --build

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

createsuperuser:
	docker compose exec web python manage.py createsuperuser

precommit:
		docker compose exec -T web ruff check --fix .; \
		docker compose exec -T web black .; \
		
seed:
	docker compose exec web python manage.py seed_inicial

seed_massivo:
	docker compose exec web python manage.py seed_massivo

test:
	docker compose exec web pytest

bash:
	docker compose exec web bash



# Atalho livre: make cmd="python manage.py shell"
.PHONY: %
%:
	docker compose exec web $(cmd)