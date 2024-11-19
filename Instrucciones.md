# Sistema Distribuido de Taxis

## Requisitos Previos (en requirements.txt)

python-dotenv==1.0.0
pyzmq==25.1.1
matplotlib==3.8.0
pandas==2.1.1


# Crear entorno virtual

python -m venv venv

source venv/bin/activate

# Instalar dependencias:
   pip install -r requirements.txt


# Editar el archivo .env según el entorno:

# Para pruebas locales

BROKER_IP=localhost
REPLICA_IP=localhost
CENTRAL_IP=localhost

# Para máquinas virtuales/red (ejemplo)

# BROKER_IP=192.168.1.100

# REPLICA_IP=192.168.1.101

# CENTRAL_IP=192.168.1.102



## Configuración de Puertos

5555: Broker PUB (recibe mensajes)
5556: Broker SUB (distribuye mensajes)
5551: Servidor Central
5552: Servidor Réplica
5558: Health Check Central
5559: Health Check Réplica
5561: Activación de Réplica
6000+: Puertos de Taxis (6001, 6002, etc.)