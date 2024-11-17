# Sistema Distribuido de Taxis

## Requisitos Previos

1. Python 3.x
2. pip (gestor de paquetes de Python)

3. Crear y activar entorno virtual:

# Crear entorno virtual

python -m venv venv

# Activar entorno virtual

# En Windows:

venv\Scripts\activate

# En Unix o MacOS:

source venv/bin/acbtivate

3. Instalar dependencias:
   pip install -r requirements.txt

4. Configurar el archivo .env:

# Copiar el archivo de ejemplo

cp .env.example .env

Editar el archivo .env según tu entorno:

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