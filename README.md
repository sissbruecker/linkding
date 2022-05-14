<div align="center">
    <br>
    <a href="https://github.com/sissbruecker/linkding">
        <img src="docs/header.svg" height="50">
    </a>
    <br>
</div>

## Overview
- [Introduction](#introduction)
- [Installation](#installation)
    - [Using Docker](#using-docker)
    - [Using Docker Compose](#using-docker-compose)
    - [User Setup](#user-setup)
    - [Managed Hosting Options](#managed-hosting-options)
- [Documentation](#documentation)
- [Browser Extension](#browser-extension)
- [Community](#community)
- [Development](#development)

##  Introduction

linkding is a simple bookmark service that you can host yourself.
It's designed be to be minimal, fast, and easy to set up using Docker.

The name comes from:
- *link* which is often used as a synonym for URLs and bookmarks in common language
- *Ding* which is German for thing
- ...so basically something for managing your links

**Feature Overview:**
- Tags for organizing bookmarks
- Search by text or tags
- Bulk editing
- Bookmark archive
- Dark mode
- Automatically creates snapshots of bookmarked websites on [the Internet Archive Wayback Machine](https://archive.org/web/)
- Automatically provides titles and descriptions of bookmarked websites
- Import and export bookmarks in Netscape HTML format
- Extensions for [Firefox](https://addons.mozilla.org/de/firefox/addon/linkding-extension/) and [Chrome](https://chrome.google.com/webstore/detail/linkding-extension/beakmhbijpdhipnjhnclmhgjlddhidpe), and a bookmarklet that should work in most browsers
- REST API for developing 3rd party apps
- Admin panel for user self-service and raw data access
- Easy to set up using Docker, uses SQLite as database


**Demo:** https://demo.linkding.link/ (configured with open registration)

**Screenshot:**

![Screenshot](/docs/linkding-screenshot.png?raw=true "Screenshot")

## Installation

linkding is designed to be run with container solutions like [Docker](https://docs.docker.com/get-started/).  The Docker image is compatible with ARM platforms, so it can be run on a Raspberry Pi.

###  Using Docker

To install linkding using Docker you can just run the [latest image](https://hub.docker.com/repository/docker/sissbruecker/linkding) from Docker Hub:
```shell
docker run --name linkding -p 9090:9090 -d sissbruecker/linkding:latest
```
By default, the application runs on port `9090`, you can map it to a different host port by modifying the port mapping in the command above. If everything completed successfully, the application should now be running and can be accessed at http://localhost:9090, provided you did not change the port mapping.

Note that the command above will store the linkding SQLite database in the container, which means that deleting the container, for example when upgrading the installation, will also remove the database. For hosting an actual installation you usually want to store the database on the host system, rather than in the container. To do so, run the following command, and replace the `{host-data-folder}` placeholder with an absolute path to a folder on your host system where you want to store the linkding database:
```shell
docker run --name linkding -p 9090:9090 -v {host-data-folder}:/etc/linkding/data -d sissbruecker/linkding:latest
```

To upgrade the installation to a new version, remove the existing container, pull the latest version of the linkding Docker image, and then start a new container using the same command that you used above. There is a [shell script](https://github.com/sissbruecker/linkding/blob/master/install-linkding.sh) available to automate these steps. The script can be configured using environment variables, or you can just modify it.

To complete the setup, you still have to [create an initial user](#user-setup), so that you can access your installation.

###  Using Docker Compose

To install linkding using [Docker Compose](https://docs.docker.com/compose/), you can use the [`docker-compose.yml`](https://github.com/sissbruecker/linkding/blob/master/docker-compose.yml) file. Copy the [`.env.sample`](https://github.com/sissbruecker/linkding/blob/master/.env.sample) file to `.env`, configure the parameters, and then run:
```shell
docker-compose up -d
```

To complete the setup, you still have to [create an initial user](#user-setup), so that you can access your installation.

### User setup

For security reasons, the linkding Docker image does not provide an initial user, so you have to create one after setting up an installation. To do so, replace the credentials in the following command and run it:

**Docker**
```shell
docker exec -it linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```

**Docker Compose**
```shell
docker-compose exec linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```

The command will prompt you for a secure password. After the command has completed you can start using the application by logging into the UI with your credentials.

### Managed Hosting Options

Self-hosting web applications on your own hardware (unfortunately) still requires a lot of technical know-how, and commitment to maintenance, with regard to keeping everything up-to-date and secure. This can be a huge entry barrier for people who are interested in self-hosting linkding, but lack the technical knowledge to do so. This section is intended to provide alternatives in form of managed hosting solutions. Note that these options are usually commercial offerings, that require paying a (usually monthly) fee for the convenience of being managed by another party. The technical knowledge required to make use of individual options is going to vary, and no guarantees can be made that every option is accessible for everyone. That being said, I hope this section helps in making the application accessible to a wider audience.

- [linkding on fly.io](https://github.com/fspoettel/linkding-on-fly) - Guide for hosting a linkding installation on [fly.io](https://fly.io). By [fspoettel](https://github.com/fspoettel)

## Documentation

| Document                                                                                        | Description                                              |
|-------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| [Options](https://github.com/sissbruecker/linkding/blob/master/docs/Options.md)                 | Lists available options, and describes how to apply them |
| [Backups](https://github.com/sissbruecker/linkding/blob/master/docs/backup.md)                  | How to backup the linkding database                      |
| [Troubleshooting](https://github.com/sissbruecker/linkding/blob/master/docs/troubleshooting.md) | Advice for troubleshooting common problems               |
| [How To](https://github.com/sissbruecker/linkding/blob/master/docs/how-to.md)                   | Tips and tricks around using linking                     |
| [Admin documentation](https://github.com/sissbruecker/linkding/blob/master/docs/Admin.md)       | User documentation for the Admin UI                      |
| [API documentation](https://github.com/sissbruecker/linkding/blob/master/docs/API.md)           | Documentation for the REST API                           |

## Browser Extension

linkding comes with an official browser extension that allows to quickly add bookmarks, and search bookmarks through the browser's address bar. You can get the extension here:
- [Mozilla Addon Store](https://addons.mozilla.org/de/firefox/addon/linkding-extension/)
- [Chrome Web Store](https://chrome.google.com/webstore/detail/linkding-extension/beakmhbijpdhipnjhnclmhgjlddhidpe)

The extension is open-source as well, and can be found [here](https://github.com/sissbruecker/linkding-extension).

## Community

This section lists community projects around using linkding, in alphabetical order. If you have a project that you want to share with the linkding community, feel free to submit a PR to add your project to this section.

- [Helm Chart](https://charts.pascaliske.dev/charts/linkding/) Helm Chart for deploying linkding inside a Kubernetes cluster. By [pascaliske](https://github.com/pascaliske)
- [linkding-extension](https://github.com/jeroenpardon/linkding-extension) Chromium compatible extension that wraps the linkding bookmarklet. Tested with Chrome, Edge, Brave. By [jeroenpardon](https://github.com/jeroenpardon)
- [linkding-injector](https://github.com/Fivefold/linkding-injector) Injects search results from linkding into the sidebar of search pages like google and duckduckgo. Tested with Firefox and Chrome. By [Fivefold](https://github.com/Fivefold)

## Development

The application is open source, so you are free to modify or contribute. The application is built using the Django web framework. You can get started by checking out the excellent Django docs: https://docs.djangoproject.com/en/3.2/. The `bookmarks` folder contains the actual bookmark application, `siteroot` is the Django root application. Other than that the code should be self-explanatory / standard Django stuff 🙂.

### Prerequisites
- Python 3
- Node.js

### Setup

Create a virtual environment for the application (https://docs.python.org/3/tutorial/venv.html):
```
python3 -m venv ~/environments/linkding
```
Activate the environment for your shell:
```
source ~/environments/linkding/bin/activate[.csh|.fish]
```
Within the active environment install the application dependencies from the application folder:
```
pip3 install -Ur requirements.txt
```
Install frontend dependencies:
```
npm install
```
Initialize database:
```
mkdir -p data
python3 manage.py migrate
```
Create a user for the frontend:
```
python3 manage.py createsuperuser --username=joe --email=joe@example.com
```
Start the Node.js development server (used for compiling JavaScript components like tag auto-completion) with:
```
npm run dev
```
Start the Django development server with:
```
python3 manage.py runserver
```
The frontend is now available under http://localhost:8000
