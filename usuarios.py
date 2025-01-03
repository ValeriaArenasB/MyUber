from config import CENTRAL_IP, CENTRAL_PORT, REPLICA_PORT, REPLICA_IP
import zmq
import time
import threading
import random

# Diccionario para almacenar el estado de los usuarios (si siguen activos o no)
usuarios_activos = {}

# Función para manejar la solicitud de taxi
def solicitar_taxi(req_socket, id_usuario, x, y):
    # Enviar solicitud de taxi
    req_socket.send_string(f"Usuario {id_usuario} en posición ({x},{y}) solicita un taxi")
    print(f"Usuario {id_usuario} ha solicitado un taxi a través del socket {req_socket.getsockopt(zmq.LAST_ENDPOINT)}.")
    
    inicio_respuesta = time.time()

    try:
        # Esperar respuesta del servidor con timeout de 15 segundos
        req_socket.setsockopt(zmq.RCVTIMEO, 15000)  # Timeout de 15 segundos
        respuesta = req_socket.recv_string()
        fin_respuesta = time.time()

        tiempo_respuesta = fin_respuesta - inicio_respuesta
        print(f"Usuario {id_usuario} recibió respuesta: {respuesta} en {tiempo_respuesta:.2f} segundos")

        # Eliminar al usuario de los activos (ha sido atendido)
        usuarios_activos[id_usuario] = False

        return True  # Indica que se recibió respuesta

    except zmq.error.Again:
        # Si no se recibe respuesta a tiempo, el usuario cancela la solicitud
        print(f"Usuario {id_usuario} no recibió respuesta en el tiempo esperado (timeout de 15 segundos). Cancelando solicitud.")
        usuarios_activos[id_usuario] = False  # Marca al usuario como inactivo (timeout)
        return False  # Indica que no se recibió respuesta


# Función para manejar cada usuario
def usuario(id_usuario, x, y, tiempo_espera):
    context = zmq.Context()

    servidores = [
        (f"tcp://{CENTRAL_IP}:{CENTRAL_PORT}", "Servidor Central"),
        (f"tcp://{REPLICA_IP}:{REPLICA_PORT}", "Servidor Réplica")
    ]
    
    print(f"Usuario {id_usuario} en posición ({x},{y}) esperando {tiempo_espera} segundos para solicitar un taxi.")
    time.sleep(tiempo_espera)
    usuarios_activos[id_usuario] = True

    for direccion_servidor, nombre_servidor in servidores:
        req_socket = context.socket(zmq.REQ)
        req_socket.connect(direccion_servidor)

        # Intentar solicitar el taxi
        if solicitar_taxi(req_socket, id_usuario, x, y):
            req_socket.close()
            return  # Solicitud exitosa, el usuario finaliza
        else:
            print(f"Usuario {id_usuario} fallo en {nombre_servidor} y finaliza la solicitud.")
            req_socket.close()
            return  # Finaliza en caso de fallo

    usuarios_activos[id_usuario] = False  # Marca al usuario como inactivo si no fue atendido


# Genera múltiples usuarios a partir de un archivo de coordenadas
def generador_usuarios_desde_archivo(archivo_usuarios):
    threads = []
    
    try:
        with open(archivo_usuarios, 'r') as file:
            lineas = file.readlines()
        
        for i, linea in enumerate(lineas):
            try:
                x, y = map(int, linea.strip().split(','))
                tiempo_espera = random.randint(1, 5)  # Generar un tiempo de espera entre 1 y 5 segundos
                hilo_usuario = threading.Thread(target=usuario, args=(i, x, y, tiempo_espera))
                threads.append(hilo_usuario)
                hilo_usuario.start()
            except ValueError:
                print(f"Error: Coordenadas inválidas en la línea {i + 1}: {linea.strip()}")
    
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {archivo_usuarios}")
        return

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    archivo_usuarios = "coordenadas_usuarios.txt"  # Nombre del archivo con las coordenadas
    generador_usuarios_desde_archivo(archivo_usuarios)
