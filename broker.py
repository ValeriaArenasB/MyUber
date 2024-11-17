import zmq

def broker():
    context = zmq.Context()

    # Socket para recibir mensajes de los taxis (XSUB)
    frontend = context.socket(zmq.XSUB)
    frontend.bind("tcp://*:5555")  # Publicadores (taxis) se conectan aquí

    # Socket para enviar mensajes al servidor central (XPUB)
    backend = context.socket(zmq.XPUB)
    backend.bind("tcp://*:5556")  # Suscriptores (servidores) se conectan aquí

    print("Broker iniciado – esperando mensajes...")

    try:
        zmq.proxy(frontend, backend)
    except Exception as e:
        print(f"Error en el proxy del broker: {e}")
    finally:
        frontend.close()
        backend.close()
        context.term()

if __name__ == "__main__":
    broker()
