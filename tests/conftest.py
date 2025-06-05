import pytest
import os
import sys

# Agregar el directorio padre al path para poder importar desde src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app

@pytest.fixture
def client():
    """
    Crea un cliente de prueba para la API de FastAPI.
    """
    # Problema con versiones más recientes de httpx/starlette/fastapi 
    # Para evitar el error "TypeError: __init__() got an unexpected keyword argument 'app'"
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close() 