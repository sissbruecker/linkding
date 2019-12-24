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

The easiest way to run linkding is to use [Docker](https://docs.docker.com/get-started/). There is also the option to set up the installation manually which I do not support, but can give some pointers on below.

### Docker

To install linkding using Docker you can just run the image from the Docker registry:
```
docker run --name linkding -p 9090:9090 -d sissbruecker/linkding:latest
```
The Docker image should be compatible with ARM platforms, so it can be run on a Raspberry Pi. By default it runs on port `9090`, but you can map it to a different port by modifying the command above.

Next, you need to create a user so that you can access the frontend. Replace the credentials in the following command and run it:
```
docker exec -it linkding python manage.py createsuperuser --username=joe --email=joe@example.com
```
The command will prompt you for your password.

If everything completed successfully the application should now be running and can be accessed at http://localhost:9090, provided you did not change the port mapping. 

### Manual

If you can not or don't want to use Docker you can install the application manually on your server. To do so you can basically follow the steps from the *Development* section below while cross-referencing the Dockerfile on how to make the application production-ready.

### Hosting

The application runs in a web-server called [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) that is production-ready and that you can expose to the web. If you don't know how to configure your server to expose the application to the web there are several more steps involved. I can not support support the process here, but I can give some pointers on what to search for:
- get the app running (described in this document)
- open the port that the application is running on in your servers firewall
- depending on your network configuration, forward the opened port in your network router, so that the application can be addressed from the internet using your public IP address and the opened port

### Backups

For backups you have two options: manually or automatic.

For manual backups you can export your bookmarks from the UI and store them on a backup device or online service.

For automatic backups you want to backup the applications database. Using Docker you can [mount](https://stackoverflow.com/questions/23439126/how-to-mount-a-host-directory-in-a-docker-container) the `/etc/linkding/data` folder from the container to the host and use the backup tool of your choice to backup the contents of that folder.

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
Start the Django development server with:
```
python3 manage.py runserver
```
The frontend is now available under http://localhost:8000