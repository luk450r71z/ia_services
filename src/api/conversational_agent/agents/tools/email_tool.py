import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from langchain_core.tools import tool
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


@tool
def send_email_summary(user_responses: Dict[str, str], recipient_email: str = None) -> bool:
    """
    Envía un resumen de las respuestas del usuario por correo electrónico.
    
    Args:
        user_responses: Diccionario con las respuestas del usuario
        recipient_email: Email del destinatario (opcional, se puede configurar por defecto)
        
    Returns:
        True si el correo se envió correctamente, False en caso contrario
    """
    try:
        # Configuración del correo (estas variables deberían estar en un archivo .env)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        default_recipient = os.getenv("RECIPIENT_EMAIL")
        
        if not sender_email or not sender_password:
            print("Error: Credenciales de correo no configuradas")
            return False
            
        # Usar el destinatario por defecto si no se proporciona uno
        if not recipient_email:
            recipient_email = default_recipient
            
        if not recipient_email:
            print("Error: No se especificó un destinatario")
            return False
        
        # Crear el mensaje
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = "Resumen de Entrevista - Bot RRHH"
        
        # Crear el cuerpo del correo
        body = "Resumen de la entrevista realizada por el Bot de RRHH:\n\n"
        
        for question, answer in user_responses.items():
            if question != "timestamp":  # Excluir el timestamp del resumen
                body += f"Pregunta: {question}\n"
                body += f"Respuesta: {answer}\n\n"
        
        # Agregar timestamp si existe
        if "timestamp" in user_responses:
            body += f"Fecha y hora: {user_responses['timestamp']}\n"
        
        message.attach(MIMEText(body, "plain"))
        
        # Enviar el correo
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = message.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print(f"Correo enviado exitosamente a {recipient_email}")
        return True
        
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False


@tool
def simulate_email_send(user_responses: Dict[str, str]) -> bool:
    """
    Simula el envío de correo para pruebas (no envía realmente).
    
    Args:
        user_responses: Diccionario con las respuestas del usuario
        
    Returns:
        Siempre True (simulación)
    """
    print("=== SIMULACIÓN DE ENVÍO DE CORREO ===")
    print("Resumen de la entrevista:")
    print("-" * 40)
    
    for question, answer in user_responses.items():
        if question != "timestamp":
            print(f"P: {question}")
            print(f"R: {answer}")
            print()
    
    if "timestamp" in user_responses:
        print(f"Fecha y hora: {user_responses['timestamp']}")
    
    print("=== FIN DE SIMULACIÓN ===")
    return True


# Versiones directas (sin @tool) para uso interno
def send_email_summary_direct(user_responses: Dict[str, str], recipient_email: str = None) -> bool:
    """
    Versión directa de send_email_summary (sin decorador @tool).
    """
    return send_email_summary.func(user_responses, recipient_email)


def simulate_email_send_direct(user_responses: Dict[str, str]) -> bool:
    """
    Versión directa de simulate_email_send (sin decorador @tool).
    """
    return simulate_email_send.func(user_responses) 