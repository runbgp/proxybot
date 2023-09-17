# ProxyBot

ProxyBot is a Discord bot that automates the configuration of CloudFlare DNS records and Caddy for reverse proxying. It was created to simplify the process of setting up and managing proxies and DNS records for a lab environment.

## Features

- Automatically creates & deletes DNS records on CloudFlare.
- Automatically configures and unconfigures a reverse proxy with Caddy.
- Supports DNS-only with no proxying.
- Supports multiple proxy server locations.

## Commands

- `$locations`: Lists proxy server locations.
- `$proxy <location> <hostname> <IP:Port>`: Creates a new proxy.
- `$dns <hostname> <ip>`: Creates a new DNS record.
- `$list`: Lists proxies and DNS records that you have created.
- `$listall`: Lists all proxies and DNS records created by all users.
- `$delete <location> <hostname>`: Deletes a proxy.
- `$deletedns <hostname>`: Deletes a DNS record.

## Proxy server setup
ProxyBot was designed around using proxy servers running Ubuntu 22.04 with Caddy installed as a service. Other configurations are unsupported and may not work.
The bot uses [Paramiko](https://www.paramiko.org/), a Python implementation of SSHv2 to connect to the proxy server, update Caddy configuration files and restart the Caddy service. By default, the bot expects to log in as the user `root`

For the proxy server, I recommend using [Linode](https://www.linode.com/), and I've built a [StackScript](https://www.linode.com/docs/products/tools/stackscripts/) to make deployment very simple.

#### Deploying on Linode with a StackScript
1. Create a StackScript in your account using the following code. Replace the example email address with your email address for [Let's Encrypt](https://letsencrypt.org/) notifications.
```bash
#!/bin/bash
#<UDF name="hostname" label="The hostname for the new Linode.">
# HOSTNAME=

export DEBIAN_FRONTEND=noninteractive

hostnamectl set-hostname $HOSTNAME

apt update && apt full-upgrade -y
apt clean && apt autoclean && apt autoremove
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install caddy -y

rm /etc/caddy/Caddyfile
cat << EOF > /etc/caddy/Caddyfile
{
        email runbgp@example.com
}
import /etc/caddy/*.caddy
EOF
systemctl restart caddy
reboot
```
2. Create a new Linode using the StackScript. Ensure you define an SSH key as ProxyBot does not support password-based authentication.
3. After a few minutes, your Linode will reboot and is ready to be used with ProxyBot. Update the `proxy_list.json` file accordingly.

## Running the bot

1. Clone the repository. 
2. Install the required Python packages. `pip install -r requirements.txt`
3. Rename the `.env.example` file to `.env` and populate the following environment variables:
    - `TOKEN`: Your Discord bot token.
    - `CF_API_KEY`: Your CloudFlare API key.
    - `CF_ZONE_ID`: Your CloudFlare Zone ID.
    - `CF_DOMAIN`: Your CloudFlare domain.
    - `CF_SUBDOMAIN`: Your CloudFlare subdomain.
    - `CF_EMAIL`: Your CloudFlare email.
    - `DB_PATH`: Path to your SQLite database.
4. Populate at least one proxy server in `proxy_list.json`
4. Run the bot. `python3 proxybot.py`

## Running with Docker

### Docker Compose

1. Create a `docker-compose.yml` file using the example below.
```yaml
version: '3.8'

services:
  proxybot:
    image: ghcr.io/runbgp/proxybot:latest
    restart: unless-stopped
    container_name: proxybot
    volumes:
      - .env:/.env
      - ./ssh_keys:/proxybot/ssh_keys
      - ./proxy_list.json:/proxybot/proxy_list.json
```
2. Rename the `.env.example` file to `.env` and populate the following environment variables:
    - `TOKEN`: Your Discord bot token.
    - `CF_API_KEY`: Your CloudFlare API key.
    - `CF_ZONE_ID`: Your CloudFlare Zone ID.
    - `CF_DOMAIN`: Your CloudFlare domain.
    - `CF_SUBDOMAIN`: Your CloudFlare subdomain.
    - `CF_EMAIL`: Your CloudFlare email.
    - `DB_PATH`: Path to your SQLite database.
3. Populate at least one proxy server in `proxy_list.json`
4. Pull the latest container. `docker pull ghcr.io/runbgp/proxybot:latest`
4. Run the bot. `docker compose up -d`

## Contributing

Contributions are always welcome. Please feel free to submit an issue or a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
