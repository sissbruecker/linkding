#!/usr/bin/env bash

writehosts(){
  echo "\
127.0.0.1  authelia.$DOMAIN
127.0.0.1  linkding.$DOMAIN
127.0.0.1  traefik.$DOMAIN" | sudo tee -a /etc/hosts > /dev/null
}

if [ $(id -u) != 0 ]; then
  echo "The script requires root access to perform some functions such as modifying your /etc/hosts file"
  read -rp "Would you like to elevate access with sudo? [y/N] " confirmsudo
  if ! [[ "$confirmsudo" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Sudo elevation denied, exiting"
    exit 1
  fi
fi

DOMAIN="example.com"

MODIFIED=$(cat /etc/hosts | grep $DOMAIN && echo true || echo false)

if [[ $MODIFIED == "false" ]]; then
  writehosts
fi

sudo docker run -a stdout -v $PWD/traefik/certs:/tmp/certs authelia/authelia authelia crypto certificate rsa generate --common-name="*.${DOMAIN}" --directory=/tmp/certs/ > /dev/null
echo "Generated SSL certificate for *.$DOMAIN"

cat << EOF
Setup completed successfully.

You can start the stack with:
  docker compose up

You can then visit the following locations:
- https://linkding.$DOMAIN
- https://authelia.$DOMAIN
- https://traefik.$DOMAIN

You will need to authorize the self-signed certificate upon visiting each domain.
EOF
