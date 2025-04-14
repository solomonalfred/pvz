import asyncio
from uvicorn import Config, Server
import os

from source.app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    config = Config(app=app, host="0.0.0.0", port=8080)
    server = Server(config)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.serve())
