from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Configuración de IPs - Usar valores por defecto solo si no están en .env
BROKER_IP = os.getenv('BROKER_IP', 'localhost')
REPLICA_IP = os.getenv('REPLICA_IP', 'localhost')  # Asegúrate que esta variable existe en .env
CENTRAL_IP = os.getenv('CENTRAL_IP', 'localhost')

# Configuración de puertos
BROKER_PUB_PORT = int(os.getenv('BROKER_PUB_PORT', 5555))
BROKER_SUB_PORT = int(os.getenv('BROKER_SUB_PORT', 5556))
CENTRAL_PORT = int(os.getenv('CENTRAL_PORT', 5551))
REPLICA_PORT = int(os.getenv('REPLICA_PORT', 5552))
HEALTH_CHECK_PORT = int(os.getenv('HEALTH_CHECK_PORT', 5558))
REPLICA_HEALTH_PORT = int(os.getenv('REPLICA_HEALTH_PORT', 5559))
ACTIVATION_PORT = int(os.getenv('ACTIVATION_PORT', 5561))
TAXI_PORT_BASE = int(os.getenv('TAXI_PORT_BASE', 6000))