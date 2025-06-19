import logging
import json
from typing import Dict, List, Any
from ..utils.env_utils import load_env_variables, get_env_variable

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Maneja el envío de notificaciones por email al finalizar conversaciones.
    """
    
    def __init__(self):
        # Cargar variables de entorno
        load_env_variables()
        
        # Configuración de email
        self.smtp_server = get_env_variable("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(get_env_variable("SMTP_PORT", "587"))
        self.smtp_username = get_env_variable("SMTP_USERNAME")
        self.smtp_password = get_env_variable("SMTP_PASSWORD")
        self.from_email = get_env_variable("FROM_EMAIL", self.smtp_username)
        
        # Inicializar SMTP
        self._init_smtp()
        
        # Log de configuración
        if self.smtp_username:
            logger.info(f"📧 SMTP configured: {self.smtp_username}@{self.smtp_server}:{self.smtp_port}")
        else:
            logger.warning(f"⚠️ SMTP_USERNAME not configured - email notifications will not work")
    
    def _init_smtp(self):
        """Inicializa las importaciones SMTP"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            self.smtp = smtplib
            self.mime_text = MIMEText
            self.mime_multipart = MIMEMultipart
            logger.info(f"📧 SMTP initialized - {self.smtp_server}:{self.smtp_port}")
        except ImportError as e:
            logger.error(f"❌ Error importing SMTP modules: {e}")
            self.smtp = None
    
    async def send_completion_notifications(self, id_session: str, emails: List[str], conversation_summary: Dict) -> Dict[str, Any]:
        """
        Envía notificaciones de finalización de conversación por email.
        
        Args:
            id_session: ID de la sesión
            emails: Lista de emails a notificar
            conversation_summary: Resumen de la conversación del agente
            
        Returns:
            Dict con el resultado de las notificaciones
        """
        try:
            if not emails:
                logger.info(f"📭 No email recipients for session {id_session}")
                return {"emails_sent": 0}
            
            results = {
                "emails_sent": 0,
                "errors": []
            }
            
            # Enviar emails
            logger.info(f"📧 Sending emails to {len(emails)} recipients for session {id_session}")
            
            try:
                self._send_completion_emails(emails, {"id_session": id_session}, conversation_summary)
                results["emails_sent"] = len(emails)
                logger.info(f"✅ Emails sent successfully for session {id_session}")
            except Exception as e:
                logger.warning(f"⚠️ Error sending emails for session {id_session}")
                results["errors"].append(f"Email error: {str(e)}")
                logger.error(f"❌ Error in email sending for session {id_session}: {str(e)}")
            
            if results["emails_sent"] > 0:
                logger.info(f"📬 Notifications sent for session {id_session}: emails={results['emails_sent']}")
            else:
                logger.info(f"📭 No notifications sent for session {id_session}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error sending notifications: {str(e)}")
            return {"emails_sent": 0, "errors": [str(e)]}
    
    def _send_completion_emails(self, email_list: List[str], session_data: Dict, conversation_summary: Dict):
        """Envía emails de finalización a una lista de destinatarios"""
        if not self.smtp or not self.smtp_username or not self.smtp_password:
            logger.warning("📧 SMTP credentials not configured - cannot send emails")
            return
        
        # Crear mensaje
        message = self.mime_multipart()
        message["Subject"] = f"Session {session_data['id_session']} ended"
        message["From"] = self.smtp_username
        message["To"] = ", ".join(email_list)
        
        # Crear contenido HTML mejorado
        responses = conversation_summary.get('responses', {})
        table_rows = ""
        for question, answer in responses.items():
            table_rows += f"<tr><td style='padding:8px; border:1px solid #ddd;'><strong>{question}</strong></td><td style='padding:8px; border:1px solid #ddd;'>{answer}</td></tr>"

        html_content = f"""
        <html>
        <body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;\">
            <div style=\"background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);\">
                <h2 style=\"color: #2c3e50; margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 10px;\">Questionnaire Completed</h2>
                <p style=\"margin: 15px 0;\"><strong>Session ID:</strong> {session_data['id_session']}</p>
                
                <div style=\"background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;\">
                    <h3 style=\"color: #2c3e50; margin-top: 0;\">Summary</h3>
                    <ul style=\"margin: 0; padding-left: 20px;\">
                        <li><strong>Questions asked:</strong> {conversation_summary['questions_asked']}</li>
                        <li><strong>Total questions:</strong> {conversation_summary['total_questions']}</li>
                    </ul>
                </div>
                
                <div style=\"background-color: #f8f9fa; padding: 15px; border-radius: 5px;\">
                    <h3 style=\"color: #2c3e50; margin-top: 0;\">Answers</h3>
                    <table style='width:100%; border-collapse:collapse; background:#fff;'>
                        <thead>
                            <tr style='background:#f0f0f0;'>
                                <th style='padding:8px; border:1px solid #ddd; text-align:left;'>Question</th>
                                <th style='padding:8px; border:1px solid #ddd; text-align:left;'>Answer</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Adjuntar contenido HTML
        message.attach(self.mime_text(html_content, 'html'))
        
        # Enviar emails
        successful_sends = 0
        for email in email_list:
            try:
                with self.smtp.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(message)
                    successful_sends += 1
                    logger.info(f"📧 Email enviado exitosamente a: {email}")
            except Exception as e:
                logger.error(f"❌ Error al enviar email a {email}: {str(e)}")
        
        logger.info(f"📊 Emails enviados: {successful_sends}/{len(email_list)}")

# Instancia global del servicio
notification_service = NotificationService() 