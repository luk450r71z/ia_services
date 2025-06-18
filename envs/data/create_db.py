import sqlite3
import os

# Asegurar que el directorio data existe
os.makedirs('data', exist_ok=True)

# Conectar a la base de datos (la crea si no existe)
conn = sqlite3.connect('envs/data/sessions.db')
cursor = conn.cursor()

# Crear tabla de sesiones
cursor.execute('''
CREATE TABLE IF NOT EXISTS sessions (
    id_session TEXT PRIMARY KEY,
    type TEXT CHECK(length(type) > 0 AND length(type) <= 50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('new', 'initiated', 'started', 'ended', 'expired')),
    content JSON DEFAULT '{}',
    configs JSON DEFAULT '{}',
    logs JSON DEFAULT '[]'
)
''')

# Guardar cambios y cerrar conexión
conn.commit()
conn.close()

print("✅ Base de datos creada exitosamente")



