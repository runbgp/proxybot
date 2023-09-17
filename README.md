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

## Setup

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
