from fastapi import FastAPI
from datetime import datetime, timedelta
import random
import time
import uvicorn
import threading
import json


#Clase Padre
class VirtualSensor:
    def __init__(self, name: str, min_val: float, max_val: float, unit: str):
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.historial = []
        self.lock = threading.Lock()
    
    def add_lectura(self, value: float):
        with self.lock:
            leyendo = {
                "timestamp" : datetime.now().isoformat(),
                "value" : round(value,2),
                "unit" : self.unit
            }
            self.historial.append(leyendo)
            self.limpiar_datos()
    
    def limpiar_datos(self):
        pass

    def ultimos_datos(self):
        with self.lock:
            return self.historial[-1] if self.historial else None
        
    def todos_datos(self):
        with self.lock:
            return self.historial.copy()

#Clase sensores
class SensorTemperatura(VirtualSensor):
    def __init__(self):
        super().__init__("Temperatura", 15, 35, "C")
        self.last_cleanup = datetime.now()

    def generar_valores(self) -> float:
        hora = datetime.now().hour
        if 6 <= hora < 12:
            base = 20
        elif 12 <= hora < 18:
            base = 28
        elif 18 <= hora < 22:
            base = 24
        else:
            base = 18

        variacion = random.uniform(-2,2)
        return max(self.min_val, min(self.max_val, base + variacion))
    
    def limpiar_datos(self):
        now = datetime.now()
        hora_maxima = now-timedelta(hours=24)

        datos_nuevos = []
        for registro in self.historial:
            fecha_registro = datetime.fromisoformat(registro["timestamp"])
            if fecha_registro > hora_maxima:
                datos_nuevos.append(registro)
        self.historial = datos_nuevos
        
class SensorHumedad(VirtualSensor):
    def __init__(self):
        super().__init__("Humedad", 60, 90, "%")

    def generar_valores(self) -> float:
        return random.uniform(self.min_val, self.max_val)
    
    def limpiar_datos(self):
        now = datetime.now()
        hora_maxima = now-timedelta(hours=24)

        datos_nuevos = []
        for registro in self.historial:
            fecha_registro = datetime.fromisoformat(registro["timestamp"])
            if fecha_registro > hora_maxima:
                datos_nuevos.append(registro)
        self.historial = datos_nuevos
        
class SensorPH(VirtualSensor):
    def __init__(self):
        super().__init__("pH", 5.5, 7.5, "pH")

    def generar_valores(self) -> float:
        return random.uniform(self.min_val, self.max_val)
    
    def limpiar_datos(self):
        now = datetime.now()
        hora_maxima = now-timedelta(days=3)

        datos_nuevos = []
        for registro in self.historial:
            fecha_registro = datetime.fromisoformat(registro["timestamp"])
            if fecha_registro > hora_maxima:    
                datos_nuevos.append(registro)
        self.historial = datos_nuevos

#Inicializar los sensores
temp_sensor = SensorTemperatura()
humedad_sensor = SensorHumedad()
ph_sensor = SensorPH()

running = True

def temperatura_worker():
    while running:
        temp_sensor.add_lectura(temp_sensor.generar_valores())
        time.sleep(5)

def humedad_worker():
    while running:
        humedad_sensor.add_lectura(humedad_sensor.generar_valores())
        time.sleep(2*3600)

def ph_worker():
    while running:
        ph_sensor.add_lectura(ph_sensor.generar_valores())
        time.sleep(6*3600)

#Iniciar threads
temp_thread = threading.Thread(target=temperatura_worker, daemon=True)
humedad_thread = threading.Thread(target=humedad_worker, daemon=True)
ph_thread = threading.Thread(target=ph_worker, daemon=True)
temp_thread.start()
humedad_thread.start()
ph_thread.start()

#FastAPI
app = FastAPI(title="Sistema de sensores invernadero")
@app.get("/temperatura")
def get_temperatura():
    ultimos = temp_sensor.ultimos_datos()
    ultimos_10 = temp_sensor.todos_datos()[-10:]
    return {
        "ultimos_datos":ultimos,
        "ultimos_10":ultimos_10
    }

@app.get("/humedad")
def get_humedad():
    return {
        "ultimos_datos":humedad_sensor.ultimos_datos(),
        "historial_completo":humedad_sensor.todos_datos()
    }

@app.get("/ph")
def get_ph():
    return {
        "historial_completo":ph_sensor.todos_datos()
    }

@app.post("/guardar-datos")
def guardar_datos():
    datos =  {
        "temperatura":temp_sensor.todos_datos(),
        "humedad":humedad_sensor.todos_datos(),
        "ph":ph_sensor.todos_datos()
    }

    filename = f"datos_sensores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(datos, f, indent=2)

    return {"mensaje": f"Datos guardados en {filename}"}

#Iniciar uvicorn y definir cuantos valores generar para cada sensor
if __name__ == "__main__":
    for i in range (10):
        temp_sensor.add_lectura(temp_sensor.generar_valores())
    for i in range (5):
        humedad_sensor.add_lectura(humedad_sensor.generar_valores())
    for i in range (5):
        ph_sensor.add_lectura(ph_sensor.generar_valores())


    uvicorn.run(app, host="127.0.0.1", port=8000)
