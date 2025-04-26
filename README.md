# Authentify

A Flask-based API integrated with a Discord bot for managing and verifying API keys with HWID (Hardware ID) binding, expiration handling, and rate-limited requests.

## Features

- **API Key Management**: Generate, check, and remove keys with customizable expiration times.
- **HWID Binding**: Link a unique HWID to each license key for added security.
- **Rate Limiting**: Protects endpoints with a rate-limiting mechanism to avoid abuse.
- **Discord Bot Integration**: Interact with a Discord bot for key management via slash commands.
- **Periodic Cleanup**: Automatically removes expired keys from the database every hour.
- **Authentication**: Verifies keys and HWID against a SQLite database to ensure access control.

## How It Works

1. **Flask App**: Handles the server-side logic for verifying and managing keys.
2. **Discord Bot**: Provides an easy interface for administrators to generate, check, and remove keys, as well as reset HWID bindings.
3. **SQLite Database**: Stores the keys, their expiration times, and linked HWIDs for user-specific access control.

## Usage

1. Start the Flask server to expose endpoints for key management.
2. Run the Discord bot to allow admins to generate and manage keys via commands.
3. Use the `/auth` endpoint to authenticate API requests from clients, verifying keys and HWIDs.

## Dependencies

- Flask
- Flask-Limiter
- Discord.py
- SQLite3
- Python 3.8+
