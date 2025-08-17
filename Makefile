# Mess Management System - Makefile
.PHONY: help build up down restart logs shell migrate test clean

# Variables
DOCKER_COMPOSE = docker-compose
PYTHON = python
MANAGE = $(PYTHON) manage.py

# Default target
help:
	@echo "Mess Management System - Available Commands"
	@echo "==========================================="
	@echo "Development:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs"
	@echo "  make shell       - Django shell"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run migrations"
	@echo "  make makemigrations - Create migrations"
	@echo "  make createsuperuser - Create admin user"
	@echo "  make dbshell     - PostgreSQL shell"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run tests"
	@echo "  make coverage    - Run tests with coverage"
	@echo "  make lint        - Run linters"
	@echo ""
	@echo "Production:"
	@echo "  make deploy      - Deploy to production"
	@echo "  make backup      - Backup database"
	@echo "  make restore     - Restore database"

# Development commands
build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d
	@echo "Services started. Access at http://localhost:8000"

down:
	$(DOCKER_COMPOSE) down

restart:
	$(DOCKER_COMPOSE) restart

logs:
	$(DOCKER_COMPOSE) logs -f

shell:
	$(DOCKER_COMPOSE) exec web python manage.py shell

# Database commands
migrate:
	$(DOCKER_COMPOSE) exec web python manage.py migrate

makemigrations:
	$(DOCKER_COMPOSE) exec web python manage.py makemigrations

createsuperuser:
	$(DOCKER_COMPOSE) exec web python manage.py createsuperuser

dbshell:
	$(DOCKER_COMPOSE) exec db psql -U mess_user -d mess_db

# Testing commands
test:
	$(DOCKER_COMPOSE) exec web python manage.py test

coverage:
	$(DOCKER_COMPOSE) exec web coverage run --source='.' manage.py test
	$(DOCKER_COMPOSE) exec web coverage report
	$(DOCKER_COMPOSE) exec web coverage html

lint:
	$(DOCKER_COMPOSE) exec web flake8 .
	$(DOCKER_COMPOSE) exec web black --check .
	$(DOCKER_COMPOSE) exec web isort --check-only .

format:
	$(DOCKER_COMPOSE) exec web black .
	$(DOCKER_COMPOSE) exec web isort .

# Production commands
deploy:
	@echo "Deploying to production..."
	git pull origin main
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml build
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml up -d
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml exec web python manage.py migrate
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
	@echo "Deployment complete!"

backup:
	@echo "Creating database backup..."
	$(DOCKER_COMPOSE) exec db pg_dump -U mess_user mess_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created!"

restore:
	@echo "Restoring database from backup..."
	@read -p "Enter backup filename: " backup_file; \
	$(DOCKER_COMPOSE) exec -T db psql -U mess_user mess_db < $$backup_file
	@echo "Restore complete!"

# Utility commands
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf htmlcov/
	rm -rf .coverage

# Initialize project
init:
	
	@echo "Please edit .env file with your configuration"
	make build
	make up
	make migrate
	@echo "Project initialized! Create superuser with: make createsuperuser"

# Generate staff token
generate-token:
	$(DOCKER_COMPOSE) exec web python manage.py shell -c \
		"from mess.models import StaffToken; \
		token, obj = StaffToken.create_token('Scanner Device 1'); \
		print(f'Token created: {token}')"

# Run celery worker locally
celery-worker:
	celery -A config worker -l info

# Run celery beat locally
celery-beat:
	celery -A config beat -l info

# Check deployment readiness
check-deploy:
	@echo "Checking deployment readiness..."
	@echo "1. Checking environment variables..."
	@test -f .env || (echo "ERROR: .env file not found" && exit 1)
	@echo "2. Running tests..."
	@make test
	@echo "3. Checking migrations..."
	@$(DOCKER_COMPOSE) exec web python manage.py showmigrations | grep "\[ \]" && \
		echo "WARNING: Unapplied migrations found" || echo "All migrations applied"
	@echo "4. Checking static files..."
	@$(DOCKER_COMPOSE) exec web python manage.py collectstatic --noinput --dry-run
	@echo "Deployment check complete!"