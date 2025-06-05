#!/usr/bin/env python
import os
import sys
import pytest

def main():
    """
    Ejecuta todas las pruebas en el directorio de tests.
    """
    # Obtener el directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Agregar el directorio padre al path para poder importar desde src
    parent_dir = os.path.dirname(current_dir)
    sys.path.append(parent_dir)
    
    # Ejecutar pytest con los argumentos deseados
    args = [
        "-v",  # Verbose
        current_dir,  # Directorio de pruebas
        "--no-header",  # Sin cabecera
    ]
    
    exit_code = pytest.main(args)
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 