.PHONY: serve

serve:
	python manage.py runserver

tasks:
	python manage.py process_tasks

test:
	pytest -n auto

format:
	black bookmarks
	black siteroot
	npx prettier bookmarks/frontend --write
	npx prettier bookmarks/styles --write
