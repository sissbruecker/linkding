#  linkding

*linkding* is a simple bookmark service that you can host yourself.
It's designed be to be minimal, fast and easy to set up using Docker. 

The name comes from:
- *link* which is often used as a synonym for URLs and bookmarks in common language
- *Ding* which is german for *thing*
- ...so basically some thing for managing your links

**Feature Overview:**
- Tags for organizing bookmarks
- Search by text or tags
- Bulk editing
- Bookmark archive
- Dark mode
- Automatically creates snapshots of bookmarked websites on [web archive](https://archive.org/web/)
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

The easiest way to run linkding is to use [Docker](https://docs.docker.com/get-started/).  The Docker image is compatible with ARM platforms, so it can be run on a Raspberry Pi.

There is also the option to set up the installation manually which I do not support, but can give some pointers on below.

###  Docker setup

To install linkding using Docker you can just run the image from the Docker registry:
```
docker run --name linkding -p 9090:9090 -d sissbruecker/linkding:latest
```
By default the application runs on port `9090`, but you can map it to a different host port by modifying the command above.

However for **production use** you also want to mount a data folder on your system, so that the applications database is not stored in the container, but on your hosts file system. This is safer in case something happens to the container and makes it easier to update the container later on, or to run backups. To do so you can use the following extended command, where you replace `{host-data-folder}` with the absolute path to a folder on your system where you want to store the data:
```shell
docker run --name linkding -p 9090:9090 -v {host-data-folder}:/etc/linkding/data -d sissbruecker/linkding:latest
```

If everything completed successfully the application should now be running and can be accessed at http://localhost:9090, provided you did not change the port mapping. 

### Automated Docker setup

If you are using a Linux system you can use the following [shell script](https://github.com/sissbruecker/linkding/blob/master/install-linkding.sh) for an automated setup. The script does basically everything described above, but also handles updating an existing container to a new application version (technically replaces the existing container with a new container built from a newer image, while mounting the same data folder).

The script can be configured using shell variables - for more details have a look at the script itself.

###  Docker-compose setup

To install linkding using docker-compose you can use the `docker-compose.yml` file. Copy the `.env.sample` file to `.env` and set your parameters, then run:
```shell
docker-compose up -d
```

### User setup

Finally you need to create a user so that you can access the application. Replace the credentials in the following command and run it:

**Docker**
```shell
docker exec -it linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```

**Docker-compose**
```shell
docker-compose exec linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```

The command will prompt you for a secure password. After the command has completed you can start using the application by logging into the UI with your credentials.

### Manual setup

If you can not or don't want to use Docker you can install the application manually on your server. To do so you can basically follow the steps from the *Development* section below while cross-referencing the `Dockerfile` and `bootstrap.sh` on how to make the application production-ready.

### Hosting

The application runs in a web-server called [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) that is production-ready and that you can expose to the web. If you don't know how to configure your server to expose the application to the web there are several more steps involved. I can not support the process here, but I can give some pointers on what to search for:
- first get the app running (described in this document)
- open the port that the application is running on in your servers firewall
- depending on your network configuration, forward the opened port in your network router, so that the application can be addressed from the internet using your public IP address and the opened port

## Options

Check the [options document](docs/Options.md) on how to configure your linkding installation.

## Administration

Check the [administration document](docs/Admin.md) on how to use the admin app that is bundled with linkding.

## Backups

Check the [backups document](docs/backup.md) for options on how to create backups.

## How To

Check the [how-to document](docs/how-to.md) for tips and tricks around using linkding.

## API

The application provides a REST API that can be used by 3rd party applications to manage bookmarks. Check the [API docs](docs/API.md) for further information.

## Troubleshooting

**Import fails with `502 Bad Gateway`**

The default timeout for requests is 60 seconds, after which the application server will cancel the request and return the above error.
Depending on the system that the application runs on, and the number of bookmarks that need to be imported, the import may take longer than the default 60 seconds.

To increase the timeout you can configure the [`LD_REQUEST_TIMEOUT` option](Options.md#LD_REQUEST_TIMEOUT).

Note that any proxy servers that you are running in front of linkding may have their own timeout settings, which are not affected by the variable.

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

## Community

- [linkding-extension](https://github.com/jeroenpardon/linkding-extension) Chromium compatible extension that wraps the linkding bookmarklet. Tested with Chrome, Edge, Brave. By [jeroenpardon](https://github.com/jeroenpardon)
