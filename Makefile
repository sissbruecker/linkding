.PHONY: serve

init:
	uv sync
	[ -d data ] || mkdir data data/assets data/favicons data/previews
	uv run manage.py migrate
	npm install

serve:
	uv run manage.py runserver

tasks:
	uv run manage.py run_huey

test:
	uv run pytest -n auto

lint:
	uv run ruff check bookmarks

format:
	uv run ruff format bookmarks
	uv run djlint bookmarks/templates --reformat --quiet --warn
	npx prettier bookmarks/frontend --write
	npx prettier bookmarks/styles --write

prepare-e2e:
	uv run playwright install chromium
	rm -rf static
	npm run build
	uv run manage.py collectstatic --no-input

e2e:
	make prepare-e2e
	uv run pytest bookmarks/tests_e2e -n auto -o "python_files=e2e_test_*.py"

frontend:
	npm run dev
