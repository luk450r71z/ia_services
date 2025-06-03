import os
import json
from typing import List, Dict, Any
from langchain_core.tools import tool


@tool
def search_questions_file(file_path: str = "data/questions.json", id_job_offer: str = None) -> List[str]:
    """
    Busca y carga las preguntas desde un archivo local basándose en el id_job_offer.
    
    Args:
        file_path: Ruta base del archivo de preguntas
        id_job_offer: ID de la oferta de trabajo para seleccionar el archivo específico
        
    Returns:
        Lista de preguntas a realizar al usuario
    """
    try:
        # Si se proporciona id_job_offer, buscar archivo específico
        if id_job_offer:
            # Construir ruta específica para la oferta de trabajo
            base_dir = os.path.dirname(file_path) if file_path else "data"
            specific_file = os.path.join(base_dir, f"questions_{id_job_offer}.json")
            
            print(f"🔍 Buscando preguntas para oferta de trabajo: {id_job_offer}")
            print(f"📁 Archivo esperado: {specific_file}")
            
            # Intentar cargar archivo específico de la oferta de trabajo
            if os.path.exists(specific_file):
                print(f"✅ Encontrado archivo específico: {specific_file}")
                with open(specific_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict) and "questions" in data:
                    print(f"📋 Cargadas {len(data['questions'])} preguntas para oferta de trabajo {id_job_offer}")
                    return data["questions"]
                elif isinstance(data, list):
                    print(f"📋 Cargadas {len(data)} preguntas para oferta de trabajo {id_job_offer}")
                    return data
            else:
                print(f"⚠️ No se encontró archivo específico para oferta de trabajo {id_job_offer}")
                print(f"🔄 Intentando cargar archivo por defecto...")
        
        # Cargar archivo por defecto si no hay id_job_offer o no existe el específico
        default_file = file_path if file_path else "data/questions.json"
        
        # Verificar si el archivo por defecto existe
        if not os.path.exists(default_file):
            print(f"❌ No se encontró archivo de preguntas: {default_file}")
            raise FileNotFoundError(f"Archivo de preguntas no encontrado: {default_file}")
        
        # Cargar preguntas del archivo por defecto
        print(f"📂 Cargando archivo por defecto: {default_file}")
        with open(default_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, dict) and "questions" in data:
            print(f"📋 Cargadas {len(data['questions'])} preguntas del archivo por defecto")
            return data["questions"]
        elif isinstance(data, list):
            print(f"📋 Cargadas {len(data)} preguntas del archivo por defecto")
            return data
        else:
            raise ValueError("Formato de archivo no válido")
            
    except Exception as e:
        print(f"❌ Error al cargar preguntas: {e}")
        raise e


@tool
def list_available_question_files(base_path: str = "data") -> List[Dict[str, Any]]:
    """
    Lista todos los archivos de preguntas disponibles en el directorio.
    
    Args:
        base_path: Directorio base donde buscar archivos de preguntas
        
    Returns:
        Lista de diccionarios con información de archivos encontrados
    """
    try:
        if not os.path.exists(base_path):
            print(f"❌ Directorio no encontrado: {base_path}")
            return []
        
        question_files = []
        
        # Buscar archivos que empiecen con "questions"
        for filename in os.listdir(base_path):
            if filename.startswith("questions") and filename.endswith(".json"):
                file_path = os.path.join(base_path, filename)
                
                # Extraer ID de oferta de trabajo si existe
                job_offer_id = None
                if filename.startswith("questions_") and filename != "questions.json":
                    job_offer_id = filename.replace("questions_", "").replace(".json", "")
                
                # Obtener información del archivo
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    question_count = 0
                    if isinstance(data, dict) and "questions" in data:
                        question_count = len(data["questions"])
                    elif isinstance(data, list):
                        question_count = len(data)
                    
                    file_info = {
                        "filename": filename,
                        "full_path": file_path,
                        "job_offer_id": job_offer_id,
                        "question_count": question_count,
                        "file_size": os.path.getsize(file_path),
                        "is_default": filename == "questions.json"
                    }
                    
                    question_files.append(file_info)
                    
                except Exception as e:
                    print(f"⚠️ Error al leer {filename}: {e}")
        
        print(f"📁 Encontrados {len(question_files)} archivos de preguntas")
        return question_files
        
    except Exception as e:
        print(f"❌ Error al listar archivos: {e}")
        return []


# Versión directa (sin @tool) para uso interno
def search_questions_file_direct(file_path: str = "data/questions.json", id_job_offer: str = None) -> List[str]:
    """
    Versión directa de search_questions_file (sin decorador @tool).
    """
    return search_questions_file.func(file_path, id_job_offer)


def list_available_question_files_direct(base_path: str = "data") -> List[Dict[str, Any]]:
    """
    Versión directa de list_available_question_files (sin decorador @tool).
    """
    return list_available_question_files.func(base_path) 