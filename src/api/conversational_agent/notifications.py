import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from .utils.env_utils import load_env_variables, get_env_variable

logger = logging.getLogger(__name__)

# Variables globales para lazy loading
smtplib = None
MIMEText = None
MIMEMultipart = None
requests = None

class NotificationManager:
    """
    Maneja el envío de notificaciones por email y webhook al finalizar conversaciones.
    Utiliza inicialización perezosa para mejorar el tiempo de startup.
    """
    
    def __init__(self):
        # Cargar variables de entorno usando las utilidades existentes
        load_env_variables()
        
        # Solo configurar variables básicas, sin importaciones pesadas
        self._smtp_initialized = False
        self._webhook_initialized = False
        
        # Configuración de email desde variables de entorno usando env_utils
        self.smtp_server = get_env_variable("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(get_env_variable("SMTP_PORT", "587"))
        self.smtp_username = get_env_variable("SMTP_USERNAME")
        self.smtp_password = get_env_variable("SMTP_PASSWORD")
        self.from_email = get_env_variable("FROM_EMAIL", self.smtp_username)
        
        # Log de configuración (sin mostrar contraseñas)
        if self.smtp_username:
            logger.info(f"📧 SMTP configured: {self.smtp_username}@{self.smtp_server}:{self.smtp_port}")
        else:
            logger.warning(f"⚠️ SMTP_USERNAME not configured - email notifications will not work")
        
        # Configurar webhook
        self.webhook_url = get_env_variable("WEBHOOK_URL")
        if self.webhook_url:
            logger.info(f"🔗 Webhook client initialized")
        else:
            logger.warning(f"⚠️ WEBHOOK_URL not configured - webhook notifications will not work")
    
    def _initialize_smtp(self):
        """Inicializa las importaciones SMTP solo cuando se necesitan"""
        if not self._smtp_initialized:
            try:
                global smtplib, MIMEText, MIMEMultipart
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                self._smtp_initialized = True
                self.smtp = smtplib
                self.mime_text = MIMEText
                self.mime_multipart = MIMEMultipart
                logger.info(f"�� SMTP initialized - {self.smtp_server}:{self.smtp_port}")
            except ImportError as e:
                logger.error(f"❌ Error importing SMTP modules: {e}")
                self.smtp = None
    
    def _initialize_webhook(self):
        """Inicializa las importaciones de requests solo cuando se necesitan"""
        if not self._webhook_initialized:
            try:
                global requests
                import requests
                self._webhook_initialized = True
                self.requests = requests
                logger.info(f"🔗 Webhook client initialized")
            except ImportError as e:
                logger.error(f"❌ Error importing requests: {e}")
                self.requests = None
    
    async def send_completion_notifications(self, id_session: str, session_data: Dict, conversation_summary: Dict) -> Dict[str, Any]:
        """
        Envía notificaciones de finalización de conversación según la configuración.
        
        Args:
            id_session: ID de la sesión
            session_data: Datos completos de la sesión
            conversation_summary: Resumen de la conversación del agente
            
        Returns:
            Dict con el resultado de cada tipo de notificación
        """
        try:
            # Obtener configuraciones de notificación
            notification_config = session_data.get("notification_config")
            if not notification_config:
                logger.info(f"📭 No notification settings for session {id_session}")
                return {"emails_sent": 0, "webhook_sent": False}
            
            results = {
                "emails_sent": 0,
                "webhook_sent": False,
                "errors": []
            }
            
            # Enviar emails
            emails = notification_config.get("emails", [])
            if emails:
                logger.info(f"📧 Sending emails to {len(emails)} recipients for session {id_session}")
                
                try:
                    self._send_completion_emails(emails, session_data, conversation_summary)
                    results["emails_sent"] = len(emails)
                    logger.info(f"✅ Emails sent successfully for session {id_session}")
                except Exception as e:
                    logger.warning(f"⚠️ Error sending emails for session {id_session}")
                    results["errors"].append(f"Email error: {str(e)}")
                    logger.error(f"❌ Error in email sending for session {id_session}: {str(e)}")
            
            # Enviar webhook
            webhook_url = notification_config.get("webhook_url")
            if webhook_url:
                logger.info(f"🔗 Sending webhook for session {id_session} to: {webhook_url}")
                
                try:
                    self._send_completion_webhook(webhook_url, session_data, conversation_summary)
                    results["webhook_sent"] = True
                    logger.info(f"✅ Webhook sent successfully for session {id_session}")
                except Exception as e:
                    logger.warning(f"⚠️ Error sending webhook for session {id_session}")
                    results["errors"].append(f"Webhook error: {str(e)}")
                    logger.error(f"❌ Error in webhook sending for session {id_session}: {str(e)}")
            
            if results["emails_sent"] > 0 or results["webhook_sent"]:
                logger.info(f"📬 Notifications sent for session {id_session}: emails={results['emails_sent']}, webhook={results['webhook_sent']}")
            else:
                logger.info(f"📭 No notifications sent for session {id_session}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error sending notifications: {str(e)}")
            return {"emails_sent": 0, "webhook_sent": False, "errors": [str(e)]}
    
    def _send_completion_emails(self, email_list: List[str], session_data: Dict, conversation_summary: Dict):
        """Sends completion emails to a list of recipients"""
        if not self.smtp or not self.smtp_username or not self.smtp_password:
            logger.warning("📧 SMTP credentials not configured - cannot send emails")
            return
        
        # Crear mensaje
        message = self.mime_multipart()
        message["Subject"] = f"Interview Completed - Session {session_data['id_session']}"
        message["From"] = self.smtp_username
        message["To"] = ", ".join(email_list)
        
        # Crear contenido
        content = f"""
        Interview completed for session {session_data['id_session']}
        
        Summary:
        - Questions asked: {conversation_summary['questions_asked']}
        - Total questions: {conversation_summary['total_questions']}
        - Completion time: {conversation_summary['completion_time']}
        
        Responses:
        {json.dumps(conversation_summary['responses'], indent=2)}
        """
        
        message.attach(self.mime_text(content))
        
        # Enviar emails
        successful_sends = 0
        for email in email_list:
            try:
                with self.smtp.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
                    successful_sends += 1
                    logger.info(f"📧 Email sent successfully to: {email}")
            except Exception as e:
                logger.error(f"❌ Error sending email to {email}: {str(e)}")
        
        logger.info(f"📊 Emails sent: {successful_sends}/{len(email_list)}")

    def _send_completion_webhook(self, webhook_url: str, session_data: Dict, conversation_summary: Dict):
        """Sends completion webhook"""
        if not self.requests:
            logger.warning("🔗 Requests module not available - cannot send webhook")
            return
        
        try:
            # Preparar payload
            payload = {
                "session_id": session_data["id_session"],
                "service_type": session_data["service_type"],
                "completion_time": conversation_summary["completion_time"],
                "responses": conversation_summary["responses"]
            }
            
            # Enviar webhook
            response = self.requests.post(webhook_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"🔗 Webhook sent successfully - Status: {response.status_code}")
            else:
                logger.warning(f"⚠️ Webhook responded with status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error sending webhook: {str(e)}")
            raise

# Instancia global del notification manager con inicialización perezosa
_notification_manager_instance = None

def get_notification_manager():
    """
    Obtiene la instancia del notification manager usando patrón singleton lazy.
    Esto mejora el tiempo de startup del servidor.
    """
    global _notification_manager_instance
    if _notification_manager_instance is None:
        _notification_manager_instance = NotificationManager()
        logger.info("📬 NotificationManager instantiated (lazy loading)")
    return _notification_manager_instance

# Clase proxy para inicialización completamente perezosa
class LazyNotificationManager:
    """Proxy que inicializa el notification manager solo cuando se usa"""
    
    def __getattr__(self, name):
        manager = get_notification_manager()
        return getattr(manager, name)
    
    async def send_completion_notifications(self, *args, **kwargs):
        manager = get_notification_manager()
        return await manager.send_completion_notifications(*args, **kwargs)

# Instancia lazy que se puede importar
notification_manager = LazyNotificationManager() 