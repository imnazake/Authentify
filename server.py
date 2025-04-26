import sqlite3
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord import app_commands
import threading
import random
import string
import asyncio
import os

# Flask app setup
app = Flask(__name__)

# Rate Limiting
limiter = Limiter(get_remote_address, default_limits=["100 per day", "15 per hour"])
limiter.init_app(app)

# SQLite database setup
conn = sqlite3.connect('keys.db', check_same_thread=False)
cursor = conn.cursor()

# Create Keys table if it doesn't exist
cursor.execute('''
     CREATE TABLE IF NOT EXISTS keys (
        key TEXT PRIMARY KEY,
        expiration_time TEXT,
        hwid TEXT
    )
''')
conn.commit()

# API Key for authentication
API_KEY = "your-secure-api-key"

# Discord bot setup
DISCORD_TOKEN = "your-discord-bot-token"
OWNER_ID = 0  # Replace with your Discord user ID (integer)
LOGS_CHANNEL_ID = 0  # Replace with actual Discord channel ID
CMD_CHANNEL_ID = 0  # Replace with actual Discord channel ID

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Helper Functions
def authenticate_request():
    """Verify API key from headers."""
    key = request.headers.get("X-API-Key")
    return key == API_KEY

def is_key_valid(key: str) -> bool:
    """Check if a key is valid and not expired."""
    cursor.execute("SELECT expiration_time FROM keys WHERE key = ?", (key,))
    result = cursor.fetchone()

    if result:
        expiration_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        if expiration_time > datetime.now():
            return True
    return False


def authenticate_user(key: str, hwid: str) -> dict:
    """Authenticate user by key and hwid."""
    cursor.execute("SELECT expiration_time, hwid FROM keys WHERE key = ?", (key,))
    result = cursor.fetchone()

    if result:
        expiration_time_str, stored_hwid = result
        expiration_time = datetime.strptime(expiration_time_str, "%Y-%m-%d %H:%M:%S")

        if expiration_time > datetime.now():
            if stored_hwid is None:
                # First use, HWID bind
                cursor.execute("UPDATE keys SET hwid = ? WHERE key = ?", (hwid, key))
                conn.commit()
                return {"status": "allowed", "message": "HWID linked"}
            elif stored_hwid == hwid:
                # HWID matches
                return {"status": "allowed", "message": "HWID verified"}
            else:
                # HWID mismatch
                return {"status": "hwid mismatch"}
        else:
            # Key expired
            return {"status": "expired"}
    else:
        # Key not found
        return {"status": "invalid key"}


@app.route('/auth', methods=['POST'])
@limiter.limit("5 per minute")
def auth():
    """Authenticate the user by key and HWID."""
    if not authenticate_request():
        return jsonify({"status": "unauthorized"}), 401

    # Get JSON data from the request
    data = request.get_json()
    key = data.get('key')
    hwid = data.get('hwid')

    # Validate the request
    if not key or not isinstance(key, str) or not hwid or not isinstance(hwid, str):
        return jsonify({"status": "invalid request"}), 400

    # Call the authenticate function
    result = authenticate_user(key, hwid)

    # Return appropriate response based on the authentication result
    if result["status"] == "allowed":
        return jsonify(result), 200
    elif result["status"] == "hwid mismatch":
        return jsonify(result), 403
    else:
        return jsonify(result), 403


# Flask Routes
@app.route('/verify_key', methods=['POST'])
@limiter.limit("5 per minute")
def verify_key():
    """Endpoint to verify if a key is valid and associated with the correct HWID."""
    if not authenticate_request():
        return jsonify({"status": "unauthorized"}), 401

    data = request.get_json()
    key = data.get('key')
    hwid = data.get('hwid')

    if not key or not isinstance(key, str) or not hwid or not isinstance(hwid, str):
        return jsonify({"status": "invalid request"}), 400

    cursor.execute("SELECT expiration_time, hwid FROM keys WHERE key = ?", (key,))
    result = cursor.fetchone()

    if result:
        expiration_time_str, stored_hwid = result
        expiration_time = datetime.strptime(expiration_time_str, "%Y-%m-%d %H:%M:%S")
        
        if expiration_time > datetime.now():
            if stored_hwid is None:
                # First time use: bind HWID
                cursor.execute("UPDATE keys SET hwid = ? WHERE key = ?", (hwid, key))
                conn.commit()
                return jsonify({"status": "allowed", "message": "HWID linked"}), 200
            elif stored_hwid == hwid:
                # HWID matches
                return jsonify({"status": "allowed", "message": "HWID verified"}), 200
            else:
                # HWID mismatch
                return jsonify({"status": "hwid mismatch"}), 403

    return jsonify({"status": "not allowed or expired"}), 403

# Discord Bot Commands
@bot.event
async def on_ready():
    print(f"Bot {bot.user} is online and ready!")
    # Sync commands with Discord
    await bot.tree.sync()

    # Start the cleanup task
    bot.loop.create_task(cleanup_expired_keys())

# Slash Command to generate a new key
@bot.tree.command(name="generate_key", description="Generate a new random alphanumeric key with expiration time.")
@app_commands.checks.has_any_role('Administrator', 'Developer')
async def generate_key(interaction: discord.Interaction, days: int = 0, hours: int = 0, minutes: int = 0, length: int = 64):
    """
    Command to generate a new random alphanumeric key with a specified expiration time.
    You can specify days, hours, and minutes for the key's validity and optionally the key length.
    """
    try:
        # Validate key length
        if length < 8 or length > 64:
            await interaction.response.send_message("❌ Key length must be between 8 and 64 characters.")
            return

        # Calculate expiration time
        expiration_time = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes)

        # Generate a random alphanumeric key
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

        # Store the key in the database
        cursor.execute(
            "INSERT INTO keys (key, expiration_time) VALUES (?, ?)", 
            (key, expiration_time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

        # Send response
        expiration_str = expiration_time.strftime("%Y-%m-%d %H:%M:%S")
        await interaction.response.send_message(
            f"✅ Generated Key: `{key}`\n"
            f"Expires On: {expiration_str} (in {days}d {hours}h {minutes}m)"
        )

    except Exception as e:
        await interaction.response.send_message(f"❌ Error generating key: {str(e)}")

# Slash Command to remove a key
@bot.tree.command(name="remove_key", description="Remove a key.")
@app_commands.checks.has_any_role('Administrator', 'Developer')
async def remove_key(interaction: discord.Interaction, key: str):
    """Command to remove a key."""
    cursor.execute("DELETE FROM keys WHERE key = ?", (key,))
    conn.commit()
    await interaction.response.send_message(f"Key `{key}` removed successfully.")


@bot.tree.command(name="check_key", description="Checks if a key is valid or not.")
#@app_commands.checks.has_any_role('Administrator', 'Developer')
async def check_key(interaction: discord.Interaction, key: str):
    """Command to check if a key is valid and not expired."""
    cursor.execute("SELECT expiration_time FROM keys WHERE key = ?", (key,))
    result = cursor.fetchone()

    if result:
        expiration_time = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        if expiration_time > datetime.now():
            await interaction.response.send_message(f"Key `{key}` is valid. Expires on: {result[0]}")
        else:
            await interaction.response.send_message(f"Key `{key}` has expired. Expired on: {result[0]}")
    else:
        await interaction.response.send_message(f"Key `{key}` not found in the database.")


# Slash Command to list all keys
@bot.tree.command(name="list_keys", description="List all keys with expiration dates.")
@app_commands.checks.has_any_role('Administrator', 'Developer')
async def list_keys(interaction: discord.Interaction):
    """Command to list all keys with expiration dates."""
    cursor.execute("SELECT key, expiration_time FROM keys")
    keys = cursor.fetchall()

    if keys:
        key_list = "\n".join([f"{key} - Expires: {exp_time}" for key, exp_time in keys])
        await interaction.response.send_message(f"Keys:\n```\n{key_list}\n```")
    else:
        await interaction.response.send_message("No keys found.")


@bot.tree.command(name="clear_chat", description="Clear the messages in the current channel.")
@app_commands.checks.has_any_role('Administrator', 'Developer')
async def clear_chat(interaction: discord.Interaction, limit: int = 100):
    """
    Command to clear the bot's messages and the owner's messages in the current channel.
    Scans up to the specified limit of recent messages (default: 100).
    """
    try:
        # Ensure the bot has permission to manage messages
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            await interaction.response.send_message("❌ I do not have permission to manage messages.", ephemeral=True)
            return
        
        # Delete messages
        deleted = await interaction.channel.purge(
            limit=limit,
            check=lambda m: m.author == interaction.user or m.author == bot.user  # User and bot messages
        )

        # Send feedback
        feedback = await interaction.response.send_message(f"✅ Cleared {len(deleted)} messages.")
        await feedback.delete(delay=5)

    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", delete_after=5)


@bot.tree.command(name="reset_hwid", description="Reset the HWID linked to a key.")
@app_commands.checks.has_any_role('Administrator', 'Developer')
async def reset_hwid(interaction: discord.Interaction, key: str):
    """Command to reset the HWID linked to a key."""
    try:
        cursor.execute("SELECT key FROM keys WHERE key = ?", (key,))
        if cursor.fetchone() is None:
            await interaction.response.send_message(f"❌ Key `{key}` not found.")
            return
        
        cursor.execute("UPDATE keys SET hwid = NULL WHERE key = ?", (key,))
        conn.commit()
        await interaction.response.send_message(f"✅ HWID for key `{key}` has been reset.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error resetting HWID: {str(e)}")


# Periodic Cleanup of Expired Keys
async def cleanup_expired_keys():
    """Remove expired keys from the database periodically and notify in Discord."""
    while True:
        cursor.execute("DELETE FROM keys WHERE expiration_time < ?", 
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        conn.commit()
        
        # Find the channel where you want to post the message
        channel_id = LOGS_CHANNEL_ID  # Replace with the ID of your channel
        channel = bot.get_channel(channel_id)

        if channel:
            # Send message to Discord
            await channel.send("Expired keys have been cleared from the database.")
        else:
            print("Channel not found.")
        
        await asyncio.sleep(3600)  # Run every hour, non-blocking

# Run Flask and Discord bot
if __name__ == "__main__":
    # Start Flask server
    def run_flask():
        port = os.environ.get("PORT", 5000)
        app.run(host="0.0.0.0", port=int(port))

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Start Discord bot
    threading.Thread(target=cleanup_expired_keys, daemon=True).start()
    bot.run(DISCORD_TOKEN)
