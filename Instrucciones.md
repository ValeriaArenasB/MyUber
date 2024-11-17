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

source venv/bin/activate

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

Estructura del Sistema

prueba/
├── broker.py # Intermediario de mensajes
├── supervisor.py # Monitor del broker
├── servidorcentral.py # Servidor principal
├── servidorreplica.py # Servidor de respaldo
├── taxi1.py # Simulación de taxi 1
├── taxi2.py # Simulación de taxi 2
├── usuarios.py # Simulación de usuarios
├── healthcheck.py # Monitor de servidores
├── config.py # Configuración centralizada
├── requirements.txt # Dependencias del proyecto
├── .env # Variables de entorno
└── datos_taxis.json # Almacenamiento de datos

Ejecución
Iniciar los componentes en este orden:

1. Iniciar el Supervisor (inicia y monitorea el Broker):

python supervisor.py

2. Iniciar el Servidor Central:

python servidorcentral.py

3. Iniciar el Servidor Réplica:

python servidorreplica.py

NOTA: El servidor réplica está diseñado para tomar el control automáticamente si el servidor central falla.
La transición es transparente para los usuarios y taxis. El sistema realizará:

- Monitoreo continuo del servidor principal
- Detección de fallas (después de 3 intentos fallidos)
- Activación automática de la réplica como nuevo servidor principal
- Mantenimiento del estado y las conexiones existentes

4. Iniciar los Taxis:

# En diferentes terminales:

python taxi.py 1
python taxi.py 2

# También se pueden agregar más taxis si se desea:

python taxi.py 3
python taxi.py 4

5. Iniciar el Health Check:

python healthcheck.py

6. Iniciar la simulación de Usuarios:

python usuarios.py

## Configuración de Puertos

5555: Broker PUB (recibe mensajes)
5556: Broker SUB (distribuye mensajes)
5551: Servidor Central
5552: Servidor Réplica
5558: Health Check Central
5559: Health Check Réplica
5561: Activación de Réplica
6000+: Puertos de Taxis (6001, 6002, etc.)

## Si algo falla....

1. Primero, desactiva el entorno virtual si lo tienes activado:

deactivate

2. Elimina el entorno virtual actual:

rm -rf venv/

3. Crea un nuevo entorno virtual:

python -m venv venv

4. Activa el nuevo entorno virtual:

# En macOS/Linux:

source venv/bin/activate

# En Windows:

# venv\Scripts\activate

5. Actualiza pip?:

python -m pip install --upgrade pip

6. Intenta instalar los paquetes uno por uno:

pip install python-dotenv
pip install pyzmq
