from config import BROKER_IP, BROKER_PUB_PORT, TAXI_PORT_BASE
import zmq
import time
import random
import json
import sys
import logging
import socket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

JSON_FILE = 'datos_taxis.json'

def cargar_datos_archivo(json_file):
    try:
        with open(json_file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {"taxis": []}
    return data

def guardar_datos_archivo(json_file, data):
    try:
        with open(json_file, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        logger.error(f"Error al guardar datos en {json_file}: {e}")

class Taxi:
    def __init__(self, id_taxi, grid_size, initial_x, initial_y, velocity, max_services):
        self.id = id_taxi
        self.grid_size = grid_size
        self.initial_x = initial_x
        self.initial_y = initial_y
        self.x = initial_x
        self.y = initial_y
        self.velocity = velocity 
        self.max_services = max_services
        self.services_completed = 0
        
    def move_taxi(self):
        SIMULATION_SCALE = 60  
        movement_interval = 30
        distance = (self.velocity * movement_interval) / 60 
        
        # Choose movement direction
        direction = random.choice(['vertical', 'horizontal'])
        
        if direction == 'vertical':
            new_x = max(0, min(self.x + distance, self.grid_size[0] - 1))
            if new_x != self.x:
                self.x = new_x
                logger.info(f"Taxi {self.id} moved to position ({self.x:.1f}, {self.y:.1f})")
                return True
        else:
            new_y = max(0, min(self.y + distance, self.grid_size[1] - 1))
            if new_y != self.y:
                self.y = new_y
                logger.info(f"Taxi {self.id} moved to position ({self.x:.1f}, {self.y:.1f})")
                return True
        return False

    def return_to_initial_position(self):
        self.x = self.initial_x
        self.y = self.initial_y
        logger.info(f"Taxi {self.id} returned to initial position ({self.x:.1f}, {self.y:.1f})")

def mover_taxi(id_taxi, grid_size, velocidad, max_servicios):
    context = zmq.Context()
    
    # Configurar sockets
    pub_socket = context.socket(zmq.PUB)
    pub_socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
    pub_socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 300)
    pub_socket.connect(f"tcp://{BROKER_IP}:{BROKER_PUB_PORT}")
    
    rep_socket = context.socket(zmq.REP)
    rep_socket.setsockopt(zmq.TCP_KEEPALIVE, 1)
    rep_socket.setsockopt(zmq.TCP_KEEPALIVE_IDLE, 300)
    rep_socket.setsockopt(zmq.RCVTIMEO, 5000)  # Timeout de 5 segundos
    rep_socket.bind(f"tcp://*:{TAXI_PORT_BASE + id_taxi}")
    
    logger.info(f"Taxi {id_taxi} escuchando en puerto {TAXI_PORT_BASE + id_taxi}")
    
    # Obtener IP real del taxi
    try:
        hostname = socket.gethostname()
        ip_taxi = socket.gethostbyname(hostname)
        logger.info(f"Taxi {id_taxi} IP: {ip_taxi}")
    except Exception as e:
        logger.error(f"Error obteniendo IP: {e}")
        ip_taxi = 'localhost'
    
    # Cargar y validar datos desde el archivo JSON
    data = cargar_datos_archivo(JSON_FILE)
    if 'taxis' not in data:
        data['taxis'] = []  # Asegurar que exista la clave "taxis"

    try:
        # Guardar posición inicial
        taxi = Taxi(id_taxi, grid_size, random.randint(0, grid_size[0] - 1), random.randint(0, grid_size[1] - 1), velocidad, max_servicios)
        tiempo_ultimo_movimiento = time.time()
        intervalo_movimiento = 30 / velocidad  # segundos reales entre movimientos
        
        while taxi.services_completed < taxi.max_services:
            tiempo_actual = time.time()
            
            # Intentar mover el taxi
            if tiempo_actual - tiempo_ultimo_movimiento >= intervalo_movimiento:
                moved = taxi.move_taxi()
                if moved:
                    tiempo_ultimo_movimiento = tiempo_actual
                    logger.info(f"Taxi {taxi.id} se ha movido a una nueva posición.")
                else:
                    logger.warning(f"Taxi {taxi.id} no se pudo mover en esta iteración.")
            
            # Publicar la posición actual del taxi
            taxi_info = {
                "id": taxi.id,
                "x": round(taxi.x, 1),
                "y": round(taxi.y, 1),
                "ip": ip_taxi,
                "port": TAXI_PORT_BASE + id_taxi,
                "status": "available",
                "services_completed": taxi.services_completed,
                "max_services": taxi.max_services
            }
            pub_socket.send_string(f"ubicacion_taxi {taxi.id} {json.dumps(taxi_info)}")
            logger.info(f"Taxi {taxi.id} - Publicando posición actualizada: {taxi_info}")

            # Actualizar o agregar el taxi en los datos JSON
            taxi_exists = False
            for t in data['taxis']:
                if t.get('id') == taxi.id:
                    t.update(taxi_info)
                    taxi_exists = True
                    break
            if not taxi_exists:
                data['taxis'].append(taxi_info)

            # Guardar los datos actualizados en el archivo JSON
            guardar_datos_archivo(JSON_FILE, data)

            # Simular servicio si hay solicitudes
            poller = zmq.Poller()
            poller.register(rep_socket, zmq.POLLIN)
            socks = dict(poller.poll(1000))
            
            if socks.get(rep_socket) == zmq.POLLIN:
                servicio = rep_socket.recv_string()
                logger.info(f"Taxi {taxi.id} - Recibido servicio: {servicio}")
                rep_socket.send_string(f"Taxi {taxi.id} aceptando servicio")
                
                time.sleep(random.uniform(1, 3))
                taxi.return_to_initial_position()
                taxi.services_completed += 1
                logger.info(f"Taxi {taxi.id} - Servicios completados: {taxi.services_completed}/{taxi.max_services}")

            time.sleep(1)
    
    finally:
        pub_socket.close()
        rep_socket.close()
        context.term()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python taxi.py <id_taxi>")
        sys.exit(1)
        
    id_taxi = int(sys.argv[1])
    grid_size = (10, 10)
    velocidad = random.choice([1, 2, 4])
    max_servicios = 3
    logger.info(f"Iniciando Taxi {id_taxi} con velocidad {velocidad} km/h")
    mover_taxi(id_taxi, grid_size, velocidad, max_servicios)
