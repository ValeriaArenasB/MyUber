import zmq

def broker():
    context = zmq.Context()

    # Socket SUB para recibir mensajes de los taxis
    frontend = context.socket(zmq.XSUB)
    frontend.bind("tcp://*:5555")

    # Socket PUB para enviar mensajes al servidor central
    backend = context.socket(zmq.XPUB)
    backend.bind("tcp://*:5556")

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
