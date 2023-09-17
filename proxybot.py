import os
import re
import sqlite3
import paramiko
import json
import discord
import CloudFlare
from dotenv import load_dotenv
from discord.ext import commands
from discord import Embed

description = '''A Discord bot for creating DNS records on CloudFlare and a reverse proxy with Caddy.'''

load_dotenv()

TOKEN = os.getenv("TOKEN")
CF_API_KEY = os.getenv("CF_API_KEY")
CF_ZONE_ID = os.getenv("CF_ZONE_ID")
CF_DOMAIN = os.getenv("CF_DOMAIN")
CF_SUBDOMAIN = os.getenv("CF_SUBDOMAIN")
CF_EMAIL = os.getenv("CF_EMAIL")
DB_PATH = os.getenv("DB_PATH")

with open('proxy_list.json') as f:
    PROXY_LIST = json.load(f)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="$", description=description, intents=intents)

cf = CloudFlare.CloudFlare(email=CF_EMAIL, key=CF_API_KEY)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS proxies 
                    (user_id INTEGER, location TEXT, hostname TEXT, ip_port TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS dns_records 
                    (user_id INTEGER, hostname TEXT, ip TEXT)''')
except sqlite3.Error as e:
    print(f"Failed to connect to the database: {e}")
    raise

@bot.event
async def on_ready():
    message = f'Logged in to Discord as {bot.user} (ID: {bot.user.id})'
    width = len(message) + 2

    print('┌' + '─' * width + '┐')
    print('│ ' + message + ' │')
    print('└' + '─' * width + '┘')

@bot.command(
    help="Lists proxy server locations.",
    brief="Lists proxy server locations."
)
async def locations(ctx):
    embed = discord.Embed(title="Proxy Locations", color=0x00ff00)

    for key, value in PROXY_LIST.items():
        embed.add_field(name=key, value=value['location'], inline=False)

    await ctx.send(embed=embed)

@bot.command(
    help="Creates a new proxy. Example usage: $proxy us-iad myservice 100.64.0.1:80",
    brief="Creates a new proxy."
)
async def proxy(ctx, location=None, hostname=None, ip_port=None):
    missing_values = []
    if location is None:
        missing_values.append('`proxy`')
    if hostname is None:
        missing_values.append('`hostname`')
    if ip_port is None:
        missing_values.append('`IP:Port`')

    if missing_values:
        await ctx.send(f"Missing input for {', '.join(missing_values)}\nExample usage: `$proxy us-iad myservice 100.64.0.1:80`")
        return

    if location not in PROXY_LIST:
        valid_locations = []
        for key, value in PROXY_LIST.items():
            valid_locations.append(f"{key} - {value['location']}")
        locations_str = '\n'.join(valid_locations)
        
        await ctx.send(f"Invalid proxy location. Available locations:\n```{locations_str}```")
        return

    if not re.match("^[a-zA-Z0-9-]+$", hostname):
        await ctx.send("Invalid hostname. Ensure it is one word and does not contain special characters.")
        return

    ip_port_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):([0-9]{1,5})$')
    match = ip_port_pattern.match(ip_port)
    if not match:
        await ctx.send("Invalid `IP:Port` format. Ensure it's a valid IP address, followed by a port number e.g. `100.64.0.1:80`")
        return
    
    port = int(match.group(1))
    if port < 1 or port > 65535:
        await ctx.send("Invalid port number. Ensure it's between `1` and `65535`.")
        return

    cf.zones.dns_records.post(CF_ZONE_ID, data={'name':f"{hostname}.{CF_SUBDOMAIN}", 'type':'A', 'content':PROXY_LIST[location]['ip'], 'proxied':False})
    cf.zones.dns_records.post(CF_ZONE_ID, data={'name':f"{hostname}.{CF_SUBDOMAIN}", 'type':'AAAA', 'content':PROXY_LIST[location]['ipv6'], 'proxied':False})

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(PROXY_LIST[location]['ip'], username="root", key_filename=PROXY_LIST[location]['ssh_key_path'])

    reverse_proxy_config = f"""{hostname}.{CF_SUBDOMAIN}.{CF_DOMAIN} {{
        reverse_proxy {ip_port}
        header {{
            Permissions-Policy interest-cohort=()
            Strict-Transport-Security max-age=31536000;
            X-Content-Type-Options nosniff
            X-Frame-Options DENY
            Referrer-Policy no-referrer-when-downgrade
}}
}}
"""

    add_cmd = f'echo "{reverse_proxy_config}" >> /etc/caddy/{hostname}.{CF_SUBDOMAIN}.{CF_DOMAIN}.caddy'
    ssh_client.exec_command(add_cmd)

    ssh_client.exec_command('systemctl restart caddy')
    
    cursor.execute("INSERT INTO proxies VALUES (?, ?, ?, ?)", (ctx.author.id, location, hostname, ip_port))
    conn.commit()
    await ctx.send(f"Proxy for https://{hostname}.{CF_SUBDOMAIN}.{CF_DOMAIN} pointing to `{ip_port}` has been created.")

@bot.command(
    help="Creates a new DNS record. Example usage: $dns myservice",
    brief="Creates a new DNS record."
)
async def dns(ctx, hostname=None, ip=None):
    missing_values = []
    if hostname is None:
        missing_values.append('`hostname`')
    if ip is None:
        missing_values.append('`ip`')

    if missing_values:
        await ctx.send(f"Missing input for {', '.join(missing_values)}\nExample usage: `$dns myservice 100.64.0.1`")
        return

    if not re.match("^[a-zA-Z0-9-]+$", hostname):
        await ctx.send("Invalid hostname. Ensure it is one word and does not contain special characters.")
        return

    ip_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
    match = ip_pattern.match(ip)
    if not match:
        await ctx.send("Invalid `IP` format. Ensure it's a valid IP address e.g. `100.64.0.1`")
        return

    cf.zones.dns_records.post(CF_ZONE_ID, data={'name':f"{hostname}.{CF_SUBDOMAIN}", 'type':'A', 'content': ip, 'proxied':False})

    cursor.execute("INSERT INTO dns_records VALUES (?, ?, ?)", (ctx.author.id, hostname, ip))
    conn.commit()

    await ctx.send(f"DNS record for `{hostname}.{CF_SUBDOMAIN}.{CF_DOMAIN}` pointing to `{ip}` has been created.")

@bot.command(
    help="Lists proxies and DNS records that you have created.",
    brief="Lists proxies and DNS records that you have created."
)
async def list(ctx):
    cursor.execute("SELECT location, hostname, ip_port FROM proxies WHERE user_id=?", (ctx.author.id,))
    proxy_entries = cursor.fetchall()

    cursor.execute("SELECT hostname, ip FROM dns_records WHERE user_id=?", (ctx.author.id,))
    dns_entries = cursor.fetchall()

    if not proxy_entries and not dns_entries:
        await ctx.send("You have no proxies or DNS records.")
        return

    embed = Embed(title="Active Proxies and DNS Records", color=0x00ff00)

    for entry in proxy_entries:
        full_hostname = f"{entry[1]}.{CF_SUBDOMAIN}.{CF_DOMAIN}"
        embed.add_field(name=f"Proxy: {full_hostname} ({entry[0]})", value=f"{entry[2]}", inline=False)

    for entry in dns_entries:
        full_hostname = f"{entry[0]}.{CF_SUBDOMAIN}.{CF_DOMAIN}"
        embed.add_field(name=f"DNS Record: {full_hostname}", value=f"{entry[1]}", inline=False)

    await ctx.send(embed=embed)

@bot.command(
    help="Lists all proxies and DNS records created by all users.",
    brief="Lists all proxies and DNS records created by all users."
)
async def listall(ctx):
    cursor.execute("SELECT user_id, location, hostname, ip_port FROM proxies")
    proxy_entries = cursor.fetchall()

    cursor.execute("SELECT user_id, hostname, ip FROM dns_records")
    dns_entries = cursor.fetchall()

    if not proxy_entries and not dns_entries:
        await ctx.send("No proxies or DNS records found.")
        return

    embed = Embed(title="All Active Proxies and DNS Records", color=0x00ff00)

    for entry in proxy_entries:
        full_hostname = f"{entry[2]}.{CF_SUBDOMAIN}.{CF_DOMAIN}"
        embed.add_field(name=f"User {entry[0]} - Proxy: {full_hostname} ({entry[1]})", value=f"{entry[3]}", inline=False)

    for entry in dns_entries:
        full_hostname = f"{entry[1]}.{CF_SUBDOMAIN}.{CF_DOMAIN}"
        embed.add_field(name=f"User {entry[0]} - DNS Record: {full_hostname}", value=f"{entry[2]}", inline=False)

    await ctx.send(embed=embed)

@bot.command(
    help="Deletes a proxy. Example usage: $delete us-iad myservice",
    brief="Deletes a proxy."
)
async def delete(ctx, location=None, hostname=None):
    missing_values = []
    if location is None:
        missing_values.append('`proxy`')
    if hostname is None:
        missing_values.append('`hostname`')

    if missing_values:
        await ctx.send(f"Missing input for {', '.join(missing_values)}\nExample usage: `$delete us-iad myservice`")
        return

    cursor.execute("SELECT ip_port FROM proxies WHERE user_id=? AND location=? AND hostname=?", (ctx.author.id, location, hostname))
    proxy_info = cursor.fetchone()

    if not proxy_info:
        await ctx.send("No such proxy found for deletion.")
        return

    all_records = cf.zones.dns_records.get(CF_ZONE_ID)
    dns_name = f"{hostname}.{CF_SUBDOMAIN}.{CF_DOMAIN}"

    for record_type in ['A', 'AAAA']:
        matching_records = [r for r in all_records if r['name'] == dns_name and r['type'] == record_type]
        for record in matching_records:
            cf.zones.dns_records.delete(CF_ZONE_ID, record['id'])

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(PROXY_LIST[location]['ip'], username="root", key_filename=PROXY_LIST[location]['ssh_key_path'])

    remove_cmd = f'rm /etc/caddy/{hostname}.{CF_SUBDOMAIN}.{CF_DOMAIN}.caddy'
    ssh_client.exec_command(remove_cmd)
    ssh_client.exec_command('systemctl restart caddy')

    cursor.execute("DELETE FROM proxies WHERE user_id=? AND location=? AND hostname=?", (ctx.author.id, location, hostname))
    conn.commit()

    await ctx.send(f"Proxy for `{dns_name}` pointing to `{proxy_info[0]}` has been deleted.")

@bot.command(
    help="Deletes a DNS record. Example usage: $deletedns myservice",
    brief="Deletes a DNS record."
)
async def deletedns(ctx, hostname=None):
    if hostname is None:
        await ctx.send("Missing input for `hostname`\nExample usage: `$deletedns myservice`")
        return

    if not re.match("^[a-zA-Z0-9-]+$", hostname):
        await ctx.send("Invalid hostname. Ensure it is one word and does not contain special characters.")
        return

    cursor.execute("SELECT hostname FROM dns_records WHERE user_id=? AND hostname=?", (ctx.author.id, hostname))
    dns_info = cursor.fetchone()

    if not dns_info:
        await ctx.send("No such DNS record found for deletion.")
        return

    all_records = cf.zones.dns_records.get(CF_ZONE_ID)
    dns_name = f"{hostname}.{CF_SUBDOMAIN}.{CF_DOMAIN}"

    for record_type in ['A']:
        matching_records = [r for r in all_records if r['name'] == dns_name and r['type'] == record_type]
        for record in matching_records:
            cf.zones.dns_records.delete(CF_ZONE_ID, record['id'])

    cursor.execute("DELETE FROM dns_records WHERE user_id=? AND hostname=?", (ctx.author.id, hostname))
    conn.commit()

    await ctx.send(f"DNS record for `{dns_name}` has been deleted.")

bot.run(TOKEN)
