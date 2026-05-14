# Gestione sensore temperatura e umidità
# Raspberry Pico WH
# Utilizzo libreria dht
#
import dht
#
# Funzioni
#
def lettura_sensore(sensor):
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
    except OSError as e:
        raise e

    return temp, hum