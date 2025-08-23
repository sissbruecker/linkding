#!/usr/bin/env bash

uv run coverage erase
uv run coverage run manage.py test
uv run coverage report --sort=cover
