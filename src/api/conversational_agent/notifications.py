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
            logger.info(f"📧 SMTP configurado: {self.smtp_username}@{self.smtp_server}:{self.smtp_port}")
        else:
            logger.warning(f"⚠️ SMTP_USERNAME no configurado - las notificaciones por email no funcionarán")
    
    def _initialize_smtp(self):
        """Inicializa las importaciones SMTP solo cuando se necesitan"""
        if not self._smtp_initialized:
            try:
                global smtplib, MIMEText, MIMEMultipart
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                self._smtp_initialized = True
                logger.info(f"📧 SMTP inicializado - {self.smtp_server}:{self.smtp_port}")
            except ImportError as e:
                logger.error(f"❌ Error importando módulos SMTP: {e}")
                raise
    
    def _initialize_webhook(self):
        """Inicializa las importaciones de requests solo cuando se necesitan"""
        if not self._webhook_initialized:
            try:
                global requests
                import requests
                self._webhook_initialized = True
                logger.info(f"🔗 Webhook client inicializado")
            except ImportError as e:
                logger.error(f"❌ Error importando requests: {e}")
                raise
    
    async def send_completion_notifications(self, session_id: str, session_data: Dict, conversation_summary: Dict) -> Dict[str, bool]:
        """
        Envía notificaciones de finalización de conversación según la configuración.
        
        Args:
            session_id: ID de la sesión
            session_data: Datos completos de la sesión
            conversation_summary: Resumen de la conversación del agente
            
        Returns:
            Dict con el resultado de cada tipo de notificación
        """
        results = {
            "emails_sent": False,
            "webhook_sent": False,
            "errors": []
        }
        
        configs = session_data.get('configs', {})
        if not configs:
            logger.info(f"📭 No hay configuraciones de notificación para sesión {session_id}")
            return results
        
        # Preparar datos de la notificación
        notification_data = self._prepare_notification_data(session_id, session_data, conversation_summary)
        
        # Enviar emails si están configurados
        emails = configs.get('emails', [])
        if emails and isinstance(emails, list) and len(emails) > 0:
            logger.info(f"📧 Enviando emails a {len(emails)} destinatarios para sesión {session_id}")
            try:
                email_success = await self._send_email_notifications(emails, notification_data)
                results["emails_sent"] = email_success
                if email_success:
                    logger.info(f"✅ Emails enviados exitosamente para sesión {session_id}")
                else:
                    logger.warning(f"⚠️ Error enviando emails para sesión {session_id}")
                    results["errors"].append("Error enviando emails")
            except Exception as e:
                logger.error(f"❌ Error en envío de emails para sesión {session_id}: {str(e)}")
                results["errors"].append(f"Error emails: {str(e)}")
        
        # Enviar webhook si está configurado
        webhook_url = configs.get('webhook')
        if webhook_url and isinstance(webhook_url, str) and webhook_url.strip():
            logger.info(f"🔗 Enviando webhook para sesión {session_id} a: {webhook_url}")
            try:
                webhook_success = await self._send_webhook_notification(webhook_url, notification_data)
                results["webhook_sent"] = webhook_success
                if webhook_success:
                    logger.info(f"✅ Webhook enviado exitosamente para sesión {session_id}")
                else:
                    logger.warning(f"⚠️ Error enviando webhook para sesión {session_id}")
                    results["errors"].append("Error enviando webhook")
            except Exception as e:
                logger.error(f"❌ Error en envío de webhook para sesión {session_id}: {str(e)}")
                results["errors"].append(f"Error webhook: {str(e)}")
        
        # Log del resultado general
        if results["emails_sent"] or results["webhook_sent"]:
            logger.info(f"📬 Notificaciones enviadas para sesión {session_id}: emails={results['emails_sent']}, webhook={results['webhook_sent']}")
        else:
            logger.info(f"📭 No se enviaron notificaciones para sesión {session_id}")
            
        return results
    
    def _prepare_notification_data(self, session_id: str, session_data: Dict, conversation_summary: Dict) -> Dict[str, Any]:
        """
        Prepara los datos que serán enviados en las notificaciones.
        
        Args:
            session_id: ID de la sesión
            session_data: Datos de la sesión
            conversation_summary: Resumen de la conversación
            
        Returns:
            Diccionario con todos los datos para la notificación
        """
        # Manejar created_at que puede ser string o datetime
        created_at = session_data.get('created_at')
        if created_at:
            if hasattr(created_at, 'isoformat'):
                # Es un objeto datetime
                created_at_str = created_at.isoformat()
            else:
                # Ya es una cadena
                created_at_str = str(created_at)
        else:
            created_at_str = None
            
        return {
            "session_id": session_id,
            "session_type": session_data.get('type', 'unknown'),
            "completed_at": datetime.utcnow().isoformat(),
            "created_at": created_at_str,
            "conversation_summary": conversation_summary,
            "content": session_data.get('content', {}),
            "status": session_data.get('status', 'complete')
        }
    
    async def _send_email_notifications(self, email_list: List[str], notification_data: Dict) -> bool:
        """
        Envía notificaciones por email a la lista de destinatarios.
        
        Args:
            email_list: Lista de emails destino
            notification_data: Datos de la notificación
            
        Returns:
            True si se enviaron exitosamente, False en caso contrario
        """
        if not self.smtp_username or not self.smtp_password:
            logger.warning("📧 Credenciales SMTP no configuradas - no se pueden enviar emails")
            return False
        
        # Inicializar SMTP solo cuando se necesita
        self._initialize_smtp()
        
        try:
            # Crear mensaje
            subject = f"Conversación Completada - Sesión {notification_data['session_id']}"
            body = self._generate_email_body(notification_data)
            
            # Configurar servidor SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            # Enviar a cada destinatario
            successful_sends = 0
            for email in email_list:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = self.from_email
                    msg['To'] = email
                    msg['Subject'] = subject
                    
                    msg.attach(MIMEText(body, 'html'))
                    
                    server.send_message(msg)
                    successful_sends += 1
                    logger.info(f"📧 Email enviado exitosamente a: {email}")
                    
                except Exception as e:
                    logger.error(f"❌ Error enviando email a {email}: {str(e)}")
            
            server.quit()
            
            # Considerar exitoso si se envió al menos un email
            success = successful_sends > 0
            logger.info(f"📊 Emails enviados: {successful_sends}/{len(email_list)}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error configurando servidor SMTP: {str(e)}")
            return False
    
    async def _send_webhook_notification(self, webhook_url: str, notification_data: Dict) -> bool:
        """
        Envía notificación via webhook.
        
        Args:
            webhook_url: URL del webhook
            notification_data: Datos de la notificación
            
        Returns:
            True si se envió exitosamente, False en caso contrario
        """
        # Inicializar requests solo cuando se necesita
        self._initialize_webhook()
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Adaptiera-ConversationalAgent/1.0'
            }
            
            response = requests.post(
                webhook_url,
                json=notification_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"🔗 Webhook enviado exitosamente - Status: {response.status_code}")
                return True
            else:
                logger.warning(f"⚠️ Webhook respondió con status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error enviando webhook: {str(e)}")
            return False
    
    def _generate_email_body(self, notification_data: Dict) -> str:
        """
        Genera el cuerpo del email con los datos de la conversación.
        
        Args:
            notification_data: Datos de la notificación
            
        Returns:
            HTML del email
        """
        session_id = notification_data['session_id']
        session_type = notification_data['session_type']
        completed_at = notification_data['completed_at']
        summary = notification_data['conversation_summary']
        
        # Formatear respuestas si existen
        responses_html = ""
        if 'responses' in summary and summary['responses']:
            responses_html = "<h3>📝 Respuestas Recopiladas:</h3><ul>"
            for question, answer in summary['responses'].items():
                responses_html += f"<li><strong>P:</strong> {question}<br><strong>R:</strong> {answer}</li><br>"
            responses_html += "</ul>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Conversación Completada</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c5aa0;">🎯 Conversación Completada</h1>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h2>📊 Información de la Sesión</h2>
                    <p><strong>ID de Sesión:</strong> {session_id}</p>
                    <p><strong>Tipo:</strong> {session_type}</p>
                    <p><strong>Completada:</strong> {completed_at}</p>
                    <p><strong>Preguntas Realizadas:</strong> {summary.get('questions_asked', 'N/A')}</p>
                    <p><strong>Total de Mensajes:</strong> {summary.get('messages_count', 'N/A')}</p>
                </div>
                
                {responses_html}
                
                <div style="background-color: #e8f4fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3>🔗 Resumen Técnico</h3>
                    <pre style="background-color: #f9f9f9; padding: 10px; border-radius: 4px; overflow-x: auto;">
{json.dumps(summary, indent=2, ensure_ascii=False)}
                    </pre>
                </div>
                
                <hr style="margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Este email fue generado automáticamente por el sistema de agentes conversacionales de Adaptiera.
                </p>
            </div>
        </body>
        </html>
        """

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
        logger.info("📬 NotificationManager instanciado (lazy loading)")
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