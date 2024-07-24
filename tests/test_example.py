import pytest
import sys
import os
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

# Charger les variables d'environnement à partir du fichier .env
load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

@pytest.mark.asyncio
async def test_ping():
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/ping")
    assert response.status_code == 200
    assert response.json() == "pong"
