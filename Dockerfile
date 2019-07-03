FROM python:3.7-slim-stretch

# Install packages required for uswgi
RUN apt-get update
RUN apt-get -y install build-essential

# Install requirements and uwsgi server for running python web apps
WORKDIR /etc/linkdings
COPY requirements.prod.txt ./requirements.txt
RUN pip install -U pip
RUN pip install -Ur requirements.txt
RUN pip install uwsgi

# Copy application
COPY bookmarks ./bookmarks
COPY siteroot ./siteroot
COPY static ./static
COPY manage.py .
COPY uwsgi.ini .
COPY bootstrap.sh .
RUN ["chmod", "+x", "./bootstrap.sh"]

# Create data folder
RUN ["mkdir", "data"]

EXPOSE 9090

# Start uwsgi server
CMD ["./bootstrap.sh"]
