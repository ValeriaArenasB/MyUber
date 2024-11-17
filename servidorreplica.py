from config import (
    BROKER_IP, BROKER_SUB_PORT, CENTRAL_PORT, REPLICA_PORT,
    HEALTH_CHECK_PORT, REPLICA_HEALTH_PORT, ACTIVATION_PORT, TAXI_PORT_BASE
)
import zmq
import time
import json
import threading
import random
import argparse
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('ServidorReplica')

class ServidorReplica:
    def __init__(self):
        self.is_primary = False
        self.running = True
        self.context = zmq.Context()
        self.taxis = {}
        self.solicitudes = []
        self.taxis_activos = {}
        self.solicitudes_timeout = {}
        self.lock = threading.Lock()
        self.user_rep_socket = None
        self.current_port = None
        self.ping_rep_socket = None
        self.health_port = REPLICA_HEALTH_PORT
        self.poller = zmq.Poller()
        self.taxi_req_socket = None
        self.sub_socket = None
        self.is_processing_messages = False  # Nuevo flag para control de procesamiento

    def activar_replica(self):
        with self.lock:
            if not self.is_primary:
                logger.info("Activando réplica como servidor principal...")
                try:
                    # Cerrar y recrear sockets existentes
                    if self.sub_socket:
                        self.poller.unregister(self.sub_socket)
                        self.sub_socket.close()
                    if self.user_rep_socket:
                        self.poller.unregister(self.user_rep_socket)
                        self.user_rep_socket.close()
                    if self.ping_rep_socket:
                        self.poller.unregister(self.ping_rep_socket)
                        self.ping_rep_socket.close()

                    time.sleep(0.1)

                    # Reconectar al broker
                    self.sub_socket = self.context.socket(zmq.SUB)
                    self.sub_socket.connect(f"tcp://{BROKER_IP}:{BROKER_SUB_PORT}")
                    self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "ubicacion_taxi")
                    self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "estado_taxi")
                    logger.info(f"Reconectado al broker en {BROKER_IP}:{BROKER_SUB_PORT}")

                    # Crear nuevos sockets
                    self.user_rep_socket = self.context.socket(zmq.REP)
                    self.user_rep_socket.bind(f"tcp://*:{CENTRAL_PORT}")
                    logger.info(f"Binding nuevo puerto de usuarios: {CENTRAL_PORT}")
                    
                    self.ping_rep_socket = self.context.socket(zmq.REP)
                    self.ping_rep_socket.bind(f"tcp://*:{HEALTH_CHECK_PORT}")
                    
                    # Registrar sockets en el poller
                    self.poller.register(self.sub_socket, zmq.POLLIN)
                    self.poller.register(self.user_rep_socket, zmq.POLLIN)
                    self.poller.register(self.ping_rep_socket, zmq.POLLIN)
                    
                    self.is_primary = True
                    self.current_port = CENTRAL_PORT
                    self.health_port = HEALTH_CHECK_PORT
                    self.is_processing_messages = True  # Activar procesamiento
                    
                    logger.info("Réplica activada completamente como servidor principal")
                    return True
                    
                except zmq.ZMQError as e:
                    logger.error(f"Error al reconfigurar sockets: {e}")
                    return False
            return False

    def listen_for_activation(self):
        context = zmq.Context()
        activation_socket = context.socket(zmq.REP)
        activation_socket.bind(f"tcp://*:{ACTIVATION_PORT}")
        
        while self.running:
            try:
                mensaje = activation_socket.recv_string()
                if mensaje == "ping" and not self.is_primary:
                    logger.info("Recibida señal de activación")
                    if self.activar_replica():
                        activation_socket.send_string("OK_ACTIVATED")
                        logger.info("Réplica activada como servidor principal")
                    else:
                        activation_socket.send_string("ERROR")
                else:
                    activation_socket.send_string("ALREADY_PRIMARY" if self.is_primary else "ERROR")
            except zmq.ZMQError as e:
                logger.error(f"Error en socket de activación: {e}")
                time.sleep(1)
        
        activation_socket.close()

    def procesar_mensaje_taxi(self, mensaje):
        if not self.is_primary:
            return  # Solo procesar mensajes si es primario
            
        partes = mensaje.split(maxsplit=2)
        if len(partes) == 3:
            tipo, id_taxi, datos = partes
            id_taxi = int(id_taxi)
            try:
                datos_json = json.loads(datos)
                if id_taxi not in self.taxis:
                    logger.info(f"Nuevo taxi detectado: Taxi {id_taxi}")
                self.taxis[id_taxi] = datos_json
                self.taxis_activos[id_taxi] = True
                logger.info(f"Ubicación de Taxi {id_taxi}: {datos_json}")
            except json.JSONDecodeError as e:
                logger.error(f"Error al decodificar JSON: {e}")

    def solicitar_servicio_taxi(self, context, taxi_id, taxi_info):
        """
        Función separada para manejar la solicitud al taxi con mejor manejo de errores
        """
        try:
            # Obtener IP del taxi de su información
            taxi_ip = taxi_info.get('ip')
            if not taxi_ip:
                logger.error(f"No se encontró IP para taxi {taxi_id}")
                return False, "IP del taxi no disponible"

            taxi_port = TAXI_PORT_BASE + taxi_id
            taxi_address = f"tcp://{taxi_ip}:{taxi_port}"
            logger.info(f"Intentando conectar con taxi en {taxi_address}")

            # Crear socket temporal con timeout
            temp_taxi_socket = context.socket(zmq.REQ)
            temp_taxi_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 segundos timeout
            temp_taxi_socket.setsockopt(zmq.LINGER, 0)
            temp_taxi_socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
            temp_taxi_socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 300)

            try:
                temp_taxi_socket.connect(taxi_address)
                logger.info(f"Conexión establecida con {taxi_address}")
                
                # Enviar solicitud
                temp_taxi_socket.send_string("Servicio asignado")
                logger.info(f"Solicitud enviada a taxi {taxi_id}")
                
                # Esperar respuesta
                respuesta = temp_taxi_socket.recv_string()
                logger.info(f"Respuesta recibida de taxi {taxi_id}: {respuesta}")
                
                return True, respuesta

            except zmq.error.Again:
                logger.error(f"Timeout esperando respuesta del taxi {taxi_id}")
                return False, "Timeout"
            except Exception as e:
                logger.error(f"Error de conexión con taxi {taxi_id}: {str(e)}")
                return False, str(e)
            finally:
                temp_taxi_socket.close()
                logger.info(f"Conexión cerrada con taxi {taxi_id}")

        except Exception as e:
            logger.error(f"Error fatal al intentar conectar con taxi {taxi_id}: {str(e)}")
            return False, "Error interno"

    def servidor(self):
        logger.info("Iniciando servidor réplica en modo pasivo...")
        
        # Initialize sockets
        self.user_rep_socket = self.context.socket(zmq.REP)
        self.user_rep_socket.bind(f"tcp://*:{REPLICA_PORT}")
        self.current_port = REPLICA_PORT

        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{BROKER_IP}:{BROKER_SUB_PORT}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "ubicacion_taxi")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "estado_taxi")

        self.ping_rep_socket = self.context.socket(zmq.REP)
        self.ping_rep_socket.bind(f"tcp://*:{REPLICA_HEALTH_PORT}")
        
        self.taxi_req_socket = self.context.socket(zmq.REQ)

        # Registrar sockets en el poller
        self.poller.register(self.sub_socket, zmq.POLLIN)
        self.poller.register(self.user_rep_socket, zmq.POLLIN)
        self.poller.register(self.ping_rep_socket, zmq.POLLIN)

        while self.running:
            try:
                sockets = dict(self.poller.poll(1000))

                # Manejar ping primero para mejor respuesta
                if self.ping_rep_socket in sockets:
                    ping_message = self.ping_rep_socket.recv_string()
                    if ping_message == "ping":
                        logger.debug("Health check recibido, enviando pong")
                        self.ping_rep_socket.send_string("pong")

                if self.sub_socket in sockets:
                    mensaje = self.sub_socket.recv_string()
                    if self.is_primary and self.is_processing_messages:  # Verificar ambas condiciones
                        logger.info(f"Recibido mensaje del broker: {mensaje}")
                        self.procesar_mensaje_taxi(mensaje)
                    else:
                        # Mantener estado actualizado incluso en modo pasivo
                        self.actualizar_estado_interno(mensaje)

                if self.user_rep_socket in sockets:
                    try:
                        solicitud = self.user_rep_socket.recv_string()
                        if self.is_primary:
                            logger.info(f"Recibida solicitud: {solicitud}")
                            
                            if self.taxis:
                                logger.info(f"Taxis disponibles: {json.dumps(self.taxis, indent=2)}")
                                taxi_seleccionado = self.seleccionar_taxi()
                                taxi_info = self.taxis.get(taxi_seleccionado, {})
                                
                                exito, respuesta = self.solicitar_servicio_taxi(self.context, taxi_seleccionado, taxi_info)
                                
                                if exito:
                                    self.user_rep_socket.send_string(f"Taxi {taxi_seleccionado} asignado")
                                    logger.info(f"Servicio asignado exitosamente a taxi {taxi_seleccionado}")
                                else:
                                    self.user_rep_socket.send_string(f"Error: {respuesta}")
                                    logger.error(f"No se pudo asignar el servicio a taxi {taxi_seleccionado}")
                            else:
                                logger.warning("No hay taxis disponibles")
                                self.user_rep_socket.send_string("No hay taxis disponibles")
                        else:
                            self.user_rep_socket.send_string("Servidor en modo réplica")

                    except Exception as e:
                        logger.error(f"Error procesando solicitud: {str(e)}")
                        try:
                            self.user_rep_socket.send_string("Error interno del servidor")
                        except Exception as e2:
                            logger.error(f"Error enviando respuesta de error: {str(e2)}")

            except zmq.ZMQError as e:
                logger.error(f"Error en sockets: {str(e)}")
                time.sleep(1)
                continue

        # Cleanup
        for socket in [self.user_rep_socket, self.ping_rep_socket, self.sub_socket, self.taxi_req_socket]:
            if socket:
                socket.close()

    def actualizar_estado_interno(self, mensaje):
        """
        Actualizar el estado interno sin logging excesivo
        """
        try:
            partes = mensaje.split(maxsplit=2)
            if len(partes) == 3:
                tipo, id_taxi, datos = partes
                id_taxi = int(id_taxi)
                datos_json = json.loads(datos)
                self.taxis[id_taxi] = datos_json
                self.taxis_activos[id_taxi] = True
        except Exception as e:
            logger.debug(f"Error actualizando estado interno: {e}")

    def seleccionar_taxi(self):
        return random.choice(list(self.taxis.keys()))

    def user_is_still_waiting(self, solicitud):
        user_id = solicitud.split()[1]
        return time.time() <= self.solicitudes_timeout.get(user_id, 0)

    def start(self):
        # Iniciar thread de activación
        activation_thread = threading.Thread(target=self.listen_for_activation)
        activation_thread.start()

        # Iniciar servidor
        self.servidor()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor Réplica")
    parser.add_argument("--replica", action="store_true", help="Iniciar como réplica")
    args = parser.parse_args()

    servidor = ServidorReplica()
    servidor.start()
