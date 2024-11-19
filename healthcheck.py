from config import CENTRAL_IP, REPLICA_IP, HEALTH_CHECK_PORT, REPLICA_HEALTH_PORT, ACTIVATION_PORT
import zmq
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('HealthCheck')

def check_server(context, ip, port, timeout):
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(f"tcp://{ip}:{port}")
    socket.setsockopt(zmq.RCVTIMEO, timeout)
    try:
        logger.debug(f"Enviando ping a {ip}:{port}")
        socket.send_string("ping")
        response = socket.recv_string()
        socket.close()
        return response == "pong"
    except zmq.error.Again:
        logger.debug(f"Timeout esperando respuesta de {ip}:{port}")
        socket.close()
        return False
    except Exception as e:
        logger.error(f"Error checking server: {e}")
        socket.close()
        return False

def health_check():
    context = zmq.Context()
    MAX_RETRIES = 3
    TIMEOUT = 5000  # 5 segundos
    checking_primary = True
    
    while checking_primary:  # Solo mientras estemos checkeando el primario
        current_ip = CENTRAL_IP
        current_port = HEALTH_CHECK_PORT
        failures = 0
        
        for attempt in range(MAX_RETRIES):
            logger.info(f"Verificando servidor primario (intento {attempt + 1}/{MAX_RETRIES})")
            
            if check_server(context, current_ip, current_port, TIMEOUT):
                logger.info("Servidor primario respondió correctamente")
                break
            else:
                failures += 1
                logger.warning(f"Servidor primario no responde. Fallo {failures}/{MAX_RETRIES}")
                
                if failures == MAX_RETRIES:
                    logger.error("Servidor principal no responde, activando réplica...")
                    if activate_replica():
                        logger.info("Réplica activada exitosamente")
                        logger.info("Terminando health check ya que la réplica está activa")
                        return
                    else:
                        logger.error("No se pudo activar la réplica")
                
                time.sleep(1)
        
        time.sleep(2)

    context.term()

def activate_replica():
    context = zmq.Context()
    activate_socket = context.socket(zmq.REQ)
    activate_socket.connect(f"tcp://{REPLICA_IP}:{ACTIVATION_PORT}")
    activate_socket.setsockopt(zmq.RCVTIMEO, 5000)

    try:
        logger.info("Enviando señal de activación a la réplica...")
        activate_socket.send_string("ping")
        response = activate_socket.recv_string()
        return response == "OK_ACTIVATED"
    except zmq.error.Again:
        logger.error("Réplica no respondió a la activación")
        return False
    except zmq.error.ZMQError as e:
        logger.error(f"Error al activar réplica: {e}")
        return False
    finally:
        activate_socket.close()

if __name__ == "__main__":
    health_check()
