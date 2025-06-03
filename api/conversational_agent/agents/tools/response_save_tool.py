import os
import json
from typing import List, Dict, Any
from langchain_core.tools import tool
import datetime


@tool
def save_user_responses(responses: Dict[str, str], file_path: str = "envs/data/user_responses.json") -> bool:
    """
    Guarda las respuestas del usuario en un archivo local.
    
    Args:
        responses: Diccionario con las respuestas del usuario
        file_path: Ruta donde guardar las respuestas
        
    Returns:
        True si se guardó correctamente, False en caso contrario
    """
    try:
        # Crear el directorio si no existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Agregar timestamp
        responses["timestamp"] = datetime.datetime.now().isoformat()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(responses, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Respuestas guardadas correctamente en: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error al guardar respuestas: {e}")
        return False


@tool
def save_user_responses_with_metadata(
    responses: Dict[str, str], 
    file_path: str = "data/user_responses.json",
    user_id: str = None,
    job_offer_id: str = None,
    session_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Guarda las respuestas del usuario con metadatos adicionales.
    
    Args:
        responses: Diccionario con las respuestas del usuario
        file_path: Ruta donde guardar las respuestas
        user_id: ID del usuario (opcional)
        job_offer_id: ID de la oferta de trabajo (opcional)
        session_info: Información adicional de la sesión (opcional)
        
    Returns:
        Diccionario con el resultado del guardado y metadatos
    """
    try:
        # Crear el directorio si no existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Crear estructura completa con metadatos
        timestamp = datetime.datetime.now()
        data_to_save = {
            "responses": responses,
            "metadata": {
                "timestamp": timestamp.isoformat(),
                "date": timestamp.strftime("%Y-%m-%d"),
                "time": timestamp.strftime("%H:%M:%S"),
                "user_id": user_id,
                "job_offer_id": job_offer_id,
                "session_info": session_info or {}
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Respuestas con metadatos guardadas en: {file_path}")
        print(f"📊 Metadatos incluidos:")
        print(f"   👤 Usuario: {user_id or 'No especificado'}")
        print(f"   💼 Oferta de trabajo: {job_offer_id or 'No especificado'}")
        print(f"   📅 Fecha: {data_to_save['metadata']['date']}")
        print(f"   🕐 Hora: {data_to_save['metadata']['time']}")
        
        return {
            "success": True,
            "file_path": file_path,
            "timestamp": data_to_save["metadata"]["timestamp"],
            "metadata": data_to_save["metadata"]
        }
        
    except Exception as e:
        print(f"❌ Error al guardar respuestas con metadatos: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_path": file_path
        }


@tool
def append_user_responses(
    responses: Dict[str, str], 
    file_path: str = "data/user_responses_history.json",
    user_id: str = None
) -> bool:
    """
    Agrega las respuestas del usuario a un archivo de historial existente.
    
    Args:
        responses: Diccionario con las respuestas del usuario
        file_path: Ruta del archivo de historial
        user_id: ID del usuario (opcional)
        
    Returns:
        True si se agregó correctamente, False en caso contrario
    """
    try:
        # Crear el directorio si no existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Cargar datos existentes o crear lista vacía
        existing_data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]  # Convertir a lista si es necesario
            except json.JSONDecodeError:
                print("⚠️ Archivo existente corrupto, creando nuevo historial")
                existing_data = []
        
        # Crear nueva entrada
        new_entry = {
            "responses": responses,
            "timestamp": datetime.datetime.now().isoformat(),
            "user_id": user_id,
            "entry_number": len(existing_data) + 1
        }
        
        # Agregar nueva entrada
        existing_data.append(new_entry)
        
        # Guardar todo el historial
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Respuesta agregada al historial: {file_path}")
        print(f"📈 Total de entradas en historial: {len(existing_data)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al agregar respuesta al historial: {e}")
        return False


@tool
def get_response_statistics(file_path: str = "data/user_responses_history.json") -> Dict[str, Any]:
    """
    Obtiene estadísticas del archivo de respuestas.
    
    Args:
        file_path: Ruta del archivo de respuestas
        
    Returns:
        Diccionario con estadísticas del archivo
    """
    try:
        if not os.path.exists(file_path):
            return {
                "file_exists": False,
                "message": f"Archivo no encontrado: {file_path}"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir a lista si no lo es
        if not isinstance(data, list):
            data = [data]
        
        # Calcular estadísticas
        total_entries = len(data)
        unique_users = len(set(entry.get("user_id") for entry in data if entry.get("user_id")))
        
        # Fechas
        timestamps = [entry.get("timestamp") for entry in data if entry.get("timestamp")]
        first_entry = min(timestamps) if timestamps else None
        last_entry = max(timestamps) if timestamps else None
        
        file_size = os.path.getsize(file_path)
        
        stats = {
            "file_exists": True,
            "file_path": file_path,
            "file_size_bytes": file_size,
            "file_size_kb": round(file_size / 1024, 2),
            "total_entries": total_entries,
            "unique_users": unique_users,
            "first_entry": first_entry,
            "last_entry": last_entry
        }
        
        print(f"📊 Estadísticas del archivo: {file_path}")
        print(f"   📝 Total de entradas: {total_entries}")
        print(f"   👥 Usuarios únicos: {unique_users}")
        print(f"   📏 Tamaño del archivo: {stats['file_size_kb']} KB")
        
        return stats
        
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")
        return {
            "file_exists": True,
            "error": str(e),
            "file_path": file_path
        }


# Versiones directas (sin @tool) para uso interno
def save_user_responses_direct(responses: Dict[str, str], file_path: str = "data/user_responses.json") -> bool:
    """
    Versión directa de save_user_responses (sin decorador @tool).
    """
    return save_user_responses.func(responses, file_path)


def save_user_responses_with_metadata_direct(
    responses: Dict[str, str], 
    file_path: str = "data/user_responses.json",
    user_id: str = None,
    job_offer_id: str = None,
    session_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Versión directa de save_user_responses_with_metadata (sin decorador @tool).
    """
    return save_user_responses_with_metadata.func(responses, file_path, user_id, job_offer_id, session_info)


def append_user_responses_direct(
    responses: Dict[str, str], 
    file_path: str = "data/user_responses_history.json",
    user_id: str = None
) -> bool:
    """
    Versión directa de append_user_responses (sin decorador @tool).
    """
    return append_user_responses.func(responses, file_path, user_id) 