.PHONY: serve

init:
	uv sync
	uv run manage.py migrate
	npm install

serve:
	uv run manage.py runserver

tasks:
	uv run manage.py run_huey

test:
	uv run pytest -n auto

format:
	uv run black bookmarks
	uv run djlint bookmarks/templates --reformat --quiet --warn
	npx prettier bookmarks/frontend --write
	npx prettier bookmarks/styles --write

e2e:
	uv run playwright install chromium
	rm -rf static
	npm run build
	uv run manage.py collectstatic --no-input
	uv run pytest bookmarks/tests_e2e -n auto -o "python_files=e2e_test_*.py"

frontend:
	npm run dev