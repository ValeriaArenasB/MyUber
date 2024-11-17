import threading
import time
from usuarios import usuario
import random
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('StressTest')

def ejecutar_prueba_carga(num_usuarios, duracion_segundos):
    inicio = time.time()
    threads = []
    usuarios_creados = 0
    
    logger.info(f"Iniciando prueba de carga. Duración: {duracion_segundos}s, Usuarios por ráfaga: {num_usuarios}")
    
    while time.time() - inicio < duracion_segundos:
        # Crear nuevos usuarios
        for _ in range(num_usuarios):
            x = random.randint(0, 9)
            y = random.randint(0, 9)
            id_usuario = random.randint(1000, 9999)
            
            thread = threading.Thread(
                target=usuario,
                args=(id_usuario, x, y, 1)
            )
            threads.append(thread)
            thread.start()
            usuarios_creados += 1
            
            logger.debug(f"Usuario {id_usuario} creado en posición ({x}, {y})")
        
        tiempo_transcurrido = time.time() - inicio
        logger.info(f"Tiempo transcurrido: {tiempo_transcurrido:.1f}s, Usuarios creados: {usuarios_creados}")
        
        # Esperar un poco antes de la siguiente ráfaga
        time.sleep(0.5)
    
    logger.info("Esperando a que terminen todos los threads...")
    
    # Esperar a que terminen todos los threads
    for thread in threads:
        thread.join()
    
    tiempo_total = time.time() - inicio
    logger.info(f"""
    Prueba de carga finalizada:
    - Duración total: {tiempo_total:.2f} segundos
    - Usuarios totales: {usuarios_creados}
    - Promedio: {usuarios_creados/tiempo_total:.2f} usuarios/segundo
    """)

if __name__ == "__main__":
    NUM_USUARIOS_POR_RAFAGA = 10
    DURACION_PRUEBA = 60  # segundos
    
    logger.info(f"""
    Configuración de la prueba:
    - Usuarios por ráfaga: {NUM_USUARIOS_POR_RAFAGA}
    - Duración de la prueba: {DURACION_PRUEBA} segundos
    - Intervalo entre ráfagas: 0.5 segundos
    """)
    
    try:
        ejecutar_prueba_carga(NUM_USUARIOS_POR_RAFAGA, DURACION_PRUEBA)
    except KeyboardInterrupt:
        logger.warning("Prueba interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error durante la prueba: {str(e)}")
