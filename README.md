#  linkding

*linkding* is a simple bookmark service that you can host yourself. It supports managing bookmarks, categorizing them with tags and has a search function. It provides a bookmarklet for quickly adding new bookmarks while browsing the web. It also supports import / export of bookmarks in the Netscape HTML format. And that's basically it 🙂.

The name comes from:
- *link* which is often used as a synonym for URLs and bookmarks in common language
- *Ding* which is german for *thing*
- ...so basically some thing for managing your links

**Demo:** https://demo.linkding.link/ (configured with open registration)

**Screenshot:**

![Screenshot](/docs/linkding-screenshot.png?raw=true "Screenshot")

## Installation

The easiest way to run linkding is to use [Docker](https://docs.docker.com/get-started/).  The Docker image should be compatible with ARM platforms, so it can be run on a Raspberry Pi.

There is also the option to set up the installation manually which I do not support, but can give some pointers on below.

###  Docker setup

To install linkding using Docker you can just run the image from the Docker registry:
```
docker run --name linkding -p 9090:9090 -d sissbruecker/linkding:latest
```
By default the application runs on port `9090`, but you can map it to a different host port by modifying the command above.

However for **production use** you also want to mount a data folder on your system, so that the applications database is not stored in the container, but on your hosts file system. This is safer in case something happens to the container and makes it easier to update the container later on, or to run backups. To do so you can use the following extended command, where you replace `{host-data-folder}` with the absolute path to a folder on your system where you want to store the data:
```
docker run --name linkding -p 9090:9090 -v {host-data-folder}:/etc/linkding/data -d sissbruecker/linkding:latest
```

If everything completed successfully the application should now be running and can be accessed at http://localhost:9090, provided you did not change the port mapping. 

### Automated Docker setup

If you are using a Linux system you can use the following [shell script](https://github.com/sissbruecker/linkding/blob/master/install-linkding.sh) for an automated setup. The script does basically everything described above, but also handles updating an existing container to a new application version (technically replaces the existing container with a new container built from a newer image, while mounting the same data folder).

The script can be configured using using shell variables - for more details have a look at the script itself.

### User setup

Finally you need to create a user so that you can access the frontend. Replace the credentials in the following command and run it:
```
docker exec -it linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```
The command will prompt you for a secure password. After the command has completed you can start using the application by logging into the UI with your credentials.

### Manual setup

If you can not or don't want to use Docker you can install the application manually on your server. To do so you can basically follow the steps from the *Development* section below while cross-referencing the `Dockerfile` and `bootstrap.sh` on how to make the application production-ready.

### Hosting

The application runs in a web-server called [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) that is production-ready and that you can expose to the web. If you don't know how to configure your server to expose the application to the web there are several more steps involved. I can not support support the process here, but I can give some pointers on what to search for:
- first get the app running (described in this document)
- open the port that the application is running on in your servers firewall
- depending on your network configuration, forward the opened port in your network router, so that the application can be addressed from the internet using your public IP address and the opened port

### Backups

For backups you have two options: manually or automatic.

For manual backups you can export your bookmarks from the UI and store them on a backup device or online service.

For automatic backups you want to backup the applications database. As described above, for production setups you should [mount](https://stackoverflow.com/questions/23439126/how-to-mount-a-host-directory-in-a-docker-container) the `/etc/linkding/data` directory from the Docker container to a directory on your host system. You can then use a backup tool of your choice to backup the contents of that directory.

## API

The application provides a REST API that can be used by 3rd party applications to manage bookmarks. Check the [API docs](./api.md) for further information.

## Development

The application is open source, so you are free to modify or contribute. The application is built using the Django web framework. You can get started by checking out the excellent Django docs: https://docs.djangoproject.com/en/3.0/. The `bookmarks` folder contains the actual bookmark application, `siteroot` is the Django root application. Other than that the code should be self-explanatory / standard Django stuff 🙂.

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