#!/usr/bin/env bash

coverage erase
coverage run manage.py test
coverage report --sort=cover
