import json
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd

# Cargar datos del JSON
with open('datos_taxis.json', 'r') as file:
    data = json.load(file)

# Asegurar que las claves necesarias existan
taxis = data.get('taxis', [])
servicios = data.get('servicios', [])
estadisticas = data.get('estadisticas', {"servicios_satisfactorios": 0, "servicios_negados": 0})

# 1. Distribución de servicios satisfactorios y denegados
def grafico_distribucion_servicios(estadisticas):
    # Extraer las métricas de los servicios
    labels = ['Satisfactorios', 'Negados']
    valores = [
        estadisticas.get('servicios_satisfactorios', 0),
        estadisticas.get('servicios_negados', 0)
    ]

    plt.figure(figsize=(6, 6))
    plt.pie(valores, labels=labels, autopct='%1.1f%%', startangle=90, colors=['lightgreen', 'red'])
    plt.title('Distribución de servicios (Satisfactorios vs Negados)')
    plt.savefig("grafico_distribucion_servicios.png")
    plt.close()

grafico_distribucion_servicios(estadisticas)


# 2. Histograma de servicios completados por taxi
def grafico_histograma_servicios(taxis):
    servicios_completados = [taxi.get('services_completed', 0) for taxi in taxis]

    plt.figure(figsize=(8, 6))
    plt.hist(servicios_completados, bins=10, color='lightblue', edgecolor='black')
    plt.title('Distribución de servicios completados por taxi')
    plt.xlabel('Número de servicios completados')
    plt.ylabel('Frecuencia')
    plt.savefig("grafico_histograma_servicios.png")
    plt.close()

grafico_histograma_servicios(taxis)

# 3. Relación entre usuarios y taxis en el plano (Distribución)
def grafico_distribucion_posiciones(servicios):
    usuarios_pos = [(s.get('usuario', {}).get('x', 0), s.get('usuario', {}).get('y', 0)) for s in servicios]
    taxis_pos = [(s.get('taxi_posicion', {}).get('x', 0), s.get('taxi_posicion', {}).get('y', 0)) for s in servicios]

    usuarios_x, usuarios_y = zip(*usuarios_pos) if usuarios_pos else ([], [])
    taxis_x, taxis_y = zip(*taxis_pos) if taxis_pos else ([], [])

    plt.figure(figsize=(8, 6))
    plt.scatter(usuarios_x, usuarios_y, color='blue', label='Usuarios')
    plt.scatter(taxis_x, taxis_y, color='red', marker='x', label='Taxis')
    plt.title('Distribución de Usuarios y Taxis en el plano XY')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.legend()
    plt.savefig("grafico_distribucion_posiciones.png")
    plt.close()

grafico_distribucion_posiciones(servicios)

# 4. Servicios completados vs. máximos permitidos
def grafico_servicios_completados_vs_max(taxis):
    ids = [taxi.get('id', 'Desconocido') for taxi in taxis]
    completados = [taxi.get('services_completed', 0) for taxi in taxis]
    maximos = [taxi.get('max_services', 0) for taxi in taxis]

    plt.figure(figsize=(10, 6))
    plt.bar(ids, maximos, label='Servicios Máximos', alpha=0.7, color='lightgreen')
    plt.bar(ids, completados, label='Servicios Completados', alpha=0.7, color='blue')
    plt.title('Servicios Completados vs Máximos Permitidos')
    plt.xlabel('ID Taxi')
    plt.ylabel('Cantidad de Servicios')
    plt.legend()
    plt.savefig("grafico_servicios_completados_vs_max.png")
    plt.close()

grafico_servicios_completados_vs_max(taxis)

# 5. Intervalo entre solicitudes de servicio
def grafico_intervalo_solicitudes(servicios):
    horas_asignacion = [
        datetime.fromisoformat(s.get('hora_asignacion').replace("Z", ""))
        for s in servicios if 'hora_asignacion' in s
    ]
    if len(horas_asignacion) > 1:
        horas_asignacion.sort()
        intervalos = [
            (horas_asignacion[i] - horas_asignacion[i - 1]).total_seconds()
            for i in range(1, len(horas_asignacion))
        ]

        plt.figure(figsize=(8, 6))
        plt.plot(range(1, len(intervalos) + 1), intervalos, marker='o', color='purple')
        plt.title('Intervalo entre solicitudes de servicio')
        plt.xlabel('Número de intervalo')
        plt.ylabel('Tiempo (segundos)')
        plt.savefig("grafico_intervalo_solicitudes.png")
        plt.close()
    else:
        print("No hay suficientes datos para calcular intervalos entre solicitudes.")

grafico_intervalo_solicitudes(servicios)

# 6. Estadísticas generales
def imprimir_estadisticas_generales(estadisticas):
    print("\nEstadísticas Generales:")
    print(f"Servicios satisfactorios: {estadisticas.get('servicios_satisfactorios', 0)}")
    print(f"Servicios negados: {estadisticas.get('servicios_negados', 0)}")

imprimir_estadisticas_generales(estadisticas)
