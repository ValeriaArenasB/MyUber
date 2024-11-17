from config import (
    BROKER_IP, BROKER_SUB_PORT, CENTRAL_PORT, 
    HEALTH_CHECK_PORT, ACTIVATION_PORT, TAXI_PORT_BASE, REPLICA_PORT
)
import zmq
import time
import json
import threading
import random
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('ServidorCentral')

def cargar_datos_archivo(json_file):
    try:
        with open(json_file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {"taxis": [], "servicios": [], "estadisticas": {"servicios_satisfactorios": 0, "servicios_negados": 0}}
    return data

def guardar_datos_archivo(json_file, data):
    with open(json_file, 'w') as file:
        json.dump(data, file, indent=4)


def calcular_distancia(pos1, pos2):
    """
    Calcula la distancia Manhattan entre dos posiciones
    """
    return abs(pos1['x'] - pos2['x']) + abs(pos1['y'] - pos2['y'])

def seleccionar_taxi(taxis, posicion_usuario):
    """
    Selecciona el taxi más cercano a la posición del usuario
    """
    if not taxis:
        return None
    
    distancias = {
        taxi_id: calcular_distancia(posicion, posicion_usuario)
        for taxi_id, posicion in taxis.items()
    }
    
    return min(distancias.items(), key=lambda x: x[1])[0]



def sincronizar_estado(replica_socket, taxis, solicitudes, taxis_activos, solicitudes_resueltas):
    while True:
        estado = {
            'taxis': taxis,
            'solicitudes': solicitudes,
            'solicitudes_resueltas': solicitudes_resueltas,
            'taxis_activos': taxis_activos
        }
        try:
            replica_socket.send_pyobj(estado)
            logger.info("Estado sincronizado con la réplica.")
        except zmq.ZMQError as e:
            logger.error(f"Error al sincronizar estado con la réplica: {e}")
        time.sleep(3)

def solicitar_servicio_taxi(context, taxi_id, taxi_info):
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

def servidor(is_primary=True):
    logger.info("Iniciando servidor central...")
    context = zmq.Context()
    user_rep_port = CENTRAL_PORT if is_primary else REPLICA_PORT

    # Log de configuración inicial
    logger.info(f"Modo: {'Primario' if is_primary else 'Réplica'}")
    logger.info(f"Puerto de usuarios: {user_rep_port}")
    logger.info(f"Broker IP: {BROKER_IP}")
    logger.info(f"TAXI_PORT_BASE: {TAXI_PORT_BASE}")

    try:
        # Sockets for communication
        sub_socket = context.socket(zmq.SUB)
        logger.info(f"Conectando al broker en {BROKER_IP}:{BROKER_SUB_PORT}")
        sub_socket.connect(f"tcp://{BROKER_IP}:{BROKER_SUB_PORT}")
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "ubicacion_taxi")
        sub_socket.setsockopt_string(zmq.SUBSCRIBE, "estado_taxi")

        user_rep_socket = context.socket(zmq.REP)
        logger.info(f"Binding al puerto {user_rep_port}")
        user_rep_socket.bind(f"tcp://*:{user_rep_port}")

        taxi_req_socket = context.socket(zmq.REQ)
        taxi_req_socket.setsockopt(zmq.RCVTIMEO, 5000)  # Timeout de 5 segundos
        taxi_req_socket.setsockopt(zmq.LINGER, 0)  # No esperar al cerrar el socket
        logger.info("Socket de taxis configurado con timeout de 5 segundos")

        # Health-check socket
        ping_rep_socket = context.socket(zmq.REP)
        ping_rep_socket.bind(f"tcp://*:{HEALTH_CHECK_PORT}")
        logger.info(f"Health-check socket bound to port {HEALTH_CHECK_PORT}")

        taxis = {}
        solicitudes = []
        taxis_activos = {}
        solicitudes_timeout = {}
        json_file = 'datos_taxis.json'
        data = cargar_datos_archivo(json_file)

        if not is_primary:
            activate_socket = context.socket(zmq.REP)
            activate_socket.bind(f"tcp://*:{ACTIVATION_PORT}")  # Dedicated port for activation

        logger.info("Servidor iniciado como " + ("Primario" if is_primary else "Réplica"))

        poller = zmq.Poller()
        poller.register(sub_socket, zmq.POLLIN)
        poller.register(user_rep_socket, zmq.POLLIN)
        poller.register(ping_rep_socket, zmq.POLLIN)

        if not is_primary:
            poller.register(activate_socket, zmq.POLLIN)

        while True:
            sockets_activados = dict(poller.poll(1000))
            logger.debug(f"Sockets activados: {list(sockets_activados.keys())}")

            if sub_socket in sockets_activados:
                mensaje = sub_socket.recv_string()
                partes = mensaje.split(maxsplit=2)
                if len(partes) == 3:
                    tema, id_taxi, contenido = partes[0], int(partes[1]), partes[2]
                    try:
                        datos = json.loads(contenido)
                        if tema == "ubicacion_taxi":
                            # Procesar mensaje de ubicación
                            if 'x' not in datos or 'y' not in datos:
                                logger.error(f"Posición inválida para Taxi {id_taxi}: {datos}")
                                continue
                            if 'ip' not in datos or 'port' not in datos:
                                logger.error(f"Taxi {id_taxi} no tiene IP o puerto válidos: {datos}")
                                continue
                            taxis[id_taxi] = datos
                            taxis_activos[id_taxi] = True
                            logger.info(f"Taxi {id_taxi} registrado con posición: {datos}")
                        elif tema == "estado_taxi":
                            # Procesar mensaje de estado
                            if 'status' not in datos:
                                logger.error(f"Estado inválido para Taxi {id_taxi}: {datos}")
                                continue
                            if id_taxi in taxis:
                                taxis[id_taxi]['status'] = datos['status']
                                logger.info(f"Taxi {id_taxi} actualizado con estado: {datos['status']}")
                            else:
                                logger.error(f"Estado recibido para un taxi no registrado: Taxi {id_taxi}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Error al decodificar JSON para Taxi {id_taxi}: {e}")


                        if id_taxi not in taxis:
                            # Log when a new taxi is detected
                            logger.info(f"Nuevo taxi detectado: Taxi {id_taxi}")
                        taxis[id_taxi] = taxi_posicion
                        taxis_activos[id_taxi] = True
                        logger.info(f"Ubicación de Taxi {id_taxi}: {taxi_posicion}")
                        guardar_datos_archivo(json_file, data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error al decodificar JSON: {e}")


            if user_rep_socket in sockets_activados:
                try:
                    solicitud = user_rep_socket.recv_string()
                    logger.info(f"Recibida solicitud: {solicitud}")
                    
                    try:
                        partes = solicitud.split("posición (")[1].split(")")[0].split(",")
                        posicion_usuario = {'x': int(partes[0]), 'y': int(partes[1])}
                    except (IndexError, ValueError) as e:
                        logger.error(f"Error al extraer la posición del usuario: {e}")
                        user_rep_socket.send_string("Error en el formato de la solicitud")
                        continue

                    if taxis:
                        taxi_seleccionado = seleccionar_taxi(taxis, posicion_usuario)
                        if taxi_seleccionado:
                            taxi_info = taxis[taxi_seleccionado]
                            exito, respuesta = solicitar_servicio_taxi(context, taxi_seleccionado, taxi_info)
                            if exito:
                                user_rep_socket.send_string(f"Taxi {taxi_seleccionado} asignado")
                            else:
                                user_rep_socket.send_string(f"Error: {respuesta}")
                        else:
                            user_rep_socket.send_string("No hay taxis disponibles")
                    else:
                        user_rep_socket.send_string("No hay taxis disponibles")
                except Exception as e:
                    logger.error(f"Error procesando solicitud: {str(e)}")
                    user_rep_socket.send_string("Error interno del servidor")

            if ping_rep_socket in sockets_activados:
                ping_message = ping_rep_socket.recv_string()
                if ping_message == "ping":
                    ping_rep_socket.send_string("pong")

            if not is_primary and activate_socket in sockets_activados:
                activate_message = activate_socket.recv_string()
                if activate_message == "ping":
                    logger.info("Activando la réplica como servidor principal.")
                    activate_socket.send_string("pong")
                    poller.unregister(activate_socket)
                    break

            time.sleep(0.1)  # Pequeña pausa para evitar consumo excesivo de CPU

    except Exception as e:
        logger.error(f"Error fatal en el servidor: {str(e)}")
    finally:
        logger.info("Cerrando sockets...")
        for socket in [sub_socket, user_rep_socket, taxi_req_socket, ping_rep_socket]:
            try:
                socket.close()
                logger.info(f"Socket cerrado correctamente: {socket}")
            except Exception as e:
                logger.error(f"Error cerrando socket: {str(e)}")
        context.term()
        logger.info("Contexto ZMQ terminado")


def seleccionar_taxi(taxis, posicion_usuario):
    """
    Selecciona el taxi más cercano a la posición del usuario
    """
    if not taxis:
        return None
        
    distancias = {
        taxi_id: calcular_distancia(posicion, posicion_usuario)
        for taxi_id, posicion in taxis.items()
    }
    
    return min(distancias.items(), key=lambda x: x[1])[0]


def user_is_still_waiting(solicitud, solicitudes_timeout):
    user_id = solicitud.split()[1]
    return time.time() <= solicitudes_timeout.get(user_id, 0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor Central o Réplica")
    parser.add_argument("--replica", action="store_true", help="Iniciar como réplica")
    args = parser.parse_args()
    servidor(is_primary=not args.replica)
