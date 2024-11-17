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

class Taxi:
    def __init__(self, id_taxi, grid_size, initial_x, initial_y, velocity, max_services):
        self.id = id_taxi
        self.grid_size = grid_size
        self.initial_x = initial_x
        self.initial_y = initial_y
        self.x = initial_x
        self.y = initial_y
        self.velocity = velocity  # Must be 1, 2, or 4 km/h
        self.max_services = max_services
        self.services_completed = 0
        
    def move_taxi(self):
        # Convert real seconds to simulation minutes
        SIMULATION_SCALE = 60  # 1 real second = 1 simulation minute
        movement_interval = 30 * 1  # 30 simulation minutes * 1 real second
        distance = (self.velocity * movement_interval) / 60  # Distance to move in 30 minutes
        
        # Choose movement direction
        direction = random.choice(['vertical', 'horizontal'])
        
        if direction == 'vertical':
            new_x = max(0, min(self.x + distance, self.grid_size[0] - 1))
            if new_x != self.x:
                self.x = new_x
                logger.info(f"Taxi {self.id} moved to position ({self.x}, {self.y})")
                return True
        else:
            new_y = max(0, min(self.y + distance, self.grid_size[1] - 1))
            if new_y != self.y:
                self.y = new_y
                logger.info(f"Taxi {self.id} moved to position ({self.x}, {self.y})")
                return True
        return False

    def return_to_initial_position(self):
        self.x = self.initial_x
        self.y = self.initial_y
        logger.info(f"Taxi {self.id} returned to initial position ({self.x}, {self.y})")
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
                "x": taxi.x,
                "y": taxi.y,
                "ip": ip_taxi,
                "port": TAXI_PORT_BASE + id_taxi,
                "status": "available"
            }
            pub_socket.send_string(f"ubicacion_taxi {taxi.id} {json.dumps(taxi_info)}")
            logger.info(f"Taxi {taxi.id} - Publicando posición actualizada: {taxi_info}")

            # Simular servicio si hay solicitudes
            poller = zmq.Poller()
            poller.register(rep_socket, zmq.POLLIN)
            socks = dict(poller.poll(1000))
            
            if socks.get(rep_socket) == zmq.POLLIN:
                servicio = rep_socket.recv_string()
                logger.info(f"Taxi {taxi.id} - Recibido servicio: {servicio}")
                rep_socket.send_string(f"Taxi {taxi.id} aceptando servicio")
                
                # Simular servicio (tiempo aleatorio entre 1-3 segundos)
                time.sleep(random.uniform(1, 3))
                taxi.return_to_initial_position()
                taxi.services_completed += 1
                logger.info(f"Taxi {taxi.id} - Servicios completados: {taxi.services_completed}/{taxi.max_services}")

            # Esperar antes de la próxima iteración
            time.sleep(1)
    
    finally:
        pub_socket.close()
        rep_socket.close()
        context.term()


def mover_taxi_en_grilla(x, y, grid_size, velocidad):
    if velocidad == 0:
        return x, y
        
    # Velocidades válidas: 1, 2 o 4 km/h
    if velocidad not in [1, 2, 4]:
        velocidad = 1
    
    # Ajustar el movimiento según la velocidad
    # Ahora, a velocidad 1 km/h, nos movemos cada 30 segundos reales (30 minutos simulados)
    # A velocidad 2 km/h, cada 15 segundos reales
    # A velocidad 4 km/h, cada 7.5 segundos reales
    movimiento = random.choice(['vertical', 'horizontal'])
    if movimiento == 'vertical':
        delta = random.choice([-1, 1])
        nuevo_x = max(0, min(x + delta, grid_size[0] - 1))
        return nuevo_x, y
    else:
        delta = random.choice([-1, 1])
        nuevo_y = max(0, min(y + delta, grid_size[1] - 1))
        return x, nuevo_y

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python taxi.py <id_taxi>")
        sys.exit(1)
        
    id_taxi = int(sys.argv[1])
    grid_size = (10, 10)
    velocidad = random.choice([1, 2, 4])  # Velocidad aleatoria del taxi (km/h)
    max_servicios = 3
    logger.info(f"Iniciando Taxi {id_taxi} con velocidad {velocidad} km/h")
    mover_taxi(id_taxi, grid_size, velocidad, max_servicios)
