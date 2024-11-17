from config import CENTRAL_IP, CENTRAL_PORT, REPLICA_PORT, REPLICA_IP
import zmq
import time
import random
import threading

# Diccionario para almacenar el estado de los usuarios (si siguen activos o no)
usuarios_activos = {}
#ip_central='10.43.100.106'
#ip_central='localhost'


# Función para manejar la solicitud de taxi
def solicitar_taxi(req_socket, id_usuario, x, y):
    try:
        mensaje = f"Usuario {id_usuario} en posición ({x},{y}) solicita un taxi"
        req_socket.send_string(mensaje)
        print(f"Usuario {sid_usuario} ha solicitado un taxi.")
        
        inicio_respuesta = time.time()

        # Aumentar el timeout a 30 segundos
        req_socket.setsockopt(zmq.RCVTIMEO, 30000)
        respuesta = req_socket.recv_string()
        fin_respuesta = time.time()

        tiempo_respuesta = fin_respuesta - inicio_respuesta
        print(f"Usuario {id_usuario} recibió respuesta: {respuesta} en {tiempo_respuesta:.2f} segundos")
        usuarios_activos[id_usuario] = False
        return True

    except zmq.error.Again:
        print(f"Usuario {id_usuario} no recibió respuesta, se va a otro proveedor")
        usuarios_activos[id_usuario] = False
        return False


# Función usuario actualizada en usuarios.py
def usuario(id_usuario, x, y, tiempo_espera):
    context = zmq.Context()

    servidores = [
        (f"tcp://{CENTRAL_IP}:{CENTRAL_PORT}", "Servidor Central"),
        (f"tcp://{REPLICA_IP}:{REPLICA_PORT}", "Servidor Réplica")
    ]
    
    time.sleep(tiempo_espera)
    usuarios_activos[id_usuario] = True

    for direccion_servidor, nombre_servidor in servidores:
        req_socket = context.socket(zmq.REQ)
        req_socket.connect(direccion_servidor)
        print(f"Usuario {id_usuario} intentando conectarse a {nombre_servidor} ({direccion_servidor})...")
        
        if solicitar_taxi(req_socket, id_usuario, x, y):
            req_socket.close()
            return
        
        print(f"Fallo en {nombre_servidor}, intentando con otro servidor...")
        req_socket.close()
        time.sleep(1)  # Esperar un segundo antes de intentar con otro servidor


# Genera múltiples usuarios con atributos aleatorios
def generador_usuarios(num_usuarios, grid_size):
    threads = []
    for i in range(num_usuarios):
        # Generar posiciones aleatorias para los usuarios
        x, y = random.randint(0, grid_size[0] - 1), random.randint(0, grid_size[1] - 1)
        tiempo_espera = random.randint(1, 5)  # Tiempo en segundos para simular minutos
        hilo_usuario = threading.Thread(target=usuario, args=(i, x, y, tiempo_espera))
        threads.append(hilo_usuario)
        hilo_usuario.start()

    # Esperar a que todos los hilos terminen
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    num_usuarios = 3  # Número de usuarios a simular
    grid_size = (10, 10)  # Tamaño de la cuadrícula NxM
    generador_usuarios(num_usuarios, grid_size)
