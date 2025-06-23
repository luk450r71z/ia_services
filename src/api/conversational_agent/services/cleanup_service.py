import asyncio
import logging
from datetime import datetime, timedelta, timezone
from auth.db.sqlite_db import get_all_sessions_db, update_session_db

logger = logging.getLogger(__name__)

class CleanupService:
    """Servicio para limpiar sesiones expiradas automáticamente"""
    
    def __init__(self, interval_minutes: int = 5):
        self.interval_minutes = interval_minutes
        self.cleanup_task = None
        self.is_running = False
        
        # Configuración de timeouts por estado
        self.timeout_config = {
            'new': 5,      # 5 minutos para sesiones nuevas sin iniciar
            'started': 5,   # 5 minutos para sesiones iniciadas sin actividad
            'initiated': 5 # 5 minutos para sesiones iniciadas pero no comenzadas
        }
    
    async def start(self):
        """Inicia el servicio de limpieza"""
        if self.is_running:
            logger.warning("⚠️ El servicio de limpieza ya está ejecutándose")
            return
        
        logger.info(f"🚀 Iniciando servicio de limpieza (intervalo: {self.interval_minutes} minutos)")
        logger.info(f"⏰ Timeouts configurados: {self.timeout_config}")
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Detiene el servicio de limpieza"""
        if not self.is_running:
            return
        
        logger.info("🛑 Deteniendo servicio de limpieza...")
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
    
    async def _cleanup_loop(self):
        """Loop principal de limpieza"""
        while self.is_running:
            try:
                await self._cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"❌ Error en limpieza automática: {str(e)}")
            
            # Esperar antes de la siguiente limpieza
            await asyncio.sleep(self.interval_minutes * 60)
    
    async def _cleanup_expired_sessions(self):
        """Limpia las sesiones expiradas según su estado"""
        logger.info("🧹 Iniciando limpieza automática de sesiones expiradas...")
        
        # Obtener todas las sesiones
        sessions = get_all_sessions_db()
        
        if not sessions:
            logger.info("🧹 No hay sesiones en la base de datos")
            return
        
        now = datetime.now(timezone.utc)
        expired_by_status = {'new': 0, 'started': 0, 'initiated': 0}
        
        for session in sessions:
            status = session['status']
            created_at = session['created_at']
            
            # Solo procesar estados que tienen timeout configurado
            if status in self.timeout_config:
                timeout_minutes = self.timeout_config[status]
                timeout_threshold = now - timedelta(minutes=timeout_minutes)
                
                if created_at < timeout_threshold:
                    expired_by_status[status] += 1
                    
                    # Marcar como expirada
                    try:
                        update_session_db(
                            id_session=session['id_session'],
                            type_value=session.get('type', 'unknown'),
                            status="expired",
                            content=session.get('content', {}),
                            configs=session.get('configs', {})
                        )
                        logger.info(f"✅ Sesión {session['id_session']} ({status}) marcada como expirada automáticamente")
                    except Exception as e:
                        logger.error(f"❌ Error marcando sesión {session['id_session']} como expirada: {str(e)}")
        
        # Resumen de limpieza
        total_expired = sum(expired_by_status.values())
        if total_expired > 0:
            logger.info(f"🧹 Limpieza completada:")
            for status, count in expired_by_status.items():
                if count > 0:
                    logger.info(f"   - {status}: {count} sesiones")
            logger.info(f"   Total: {total_expired} sesiones expiradas")
        else:
            logger.info("🧹 No se encontraron sesiones para limpiar")
    
    def get_timeout_info(self):
        """Retorna información sobre los timeouts configurados"""
        return {
            "interval_minutes": self.interval_minutes,
            "timeouts": self.timeout_config,
            "is_running": self.is_running
        }

# Instancia global del servicio
cleanup_service = CleanupService() 