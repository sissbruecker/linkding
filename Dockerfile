FROM python:3.7-slim-stretch

# Install packages required for uswgi
RUN apt-get update
RUN apt-get -y install build-essential

# Install requirements and uwsgi server for running python web apps
WORKDIR /etc/linkding
COPY requirements.prod.txt ./requirements.txt
RUN pip install -U pip
RUN pip install -Ur requirements.txt

# Copy application
COPY . .

# Expose uwsgi server at port 9090
EXPOSE 9090

# Run bootstrap logic
RUN ["chmod", "+x", "./bootstrap.sh"]
CMD ["./bootstrap.sh"]
