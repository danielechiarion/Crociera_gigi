import socket
import json
import time
import sys
import threading
import paho.mqtt.client as mqtt

# =========================
# CARICAMENTO CONFIGURAZIONE
# =========================

try:
    with open("Configurazione/parametri.json", "r", encoding="utf-8") as file:
        parametri = json.load(file)

except Exception as e:
    print("Errore lettura parametri:", e)
    sys.exit()

TEMPO_RILEVAZIONE = parametri["TEMPO_RILEVAZIONE"]
NUMERO_DECIMALI = parametri["N_DECIMALI"]
IP_SERVER = parametri["IP_SERVER"]
PORTA_SERVER = parametri["PORTA_SERVER"]
TOPIC = parametri["TOPIC"]
BROKER = parametri["BROKER"]
PORTA_BROKER = parametri["PORTA_BROKER"]

# =========================
# CARICAMENTO TOKENS
# =========================

try:
    with open("Configurazione/tokens.json", "r", encoding="utf-8") as f:
        tokens = json.load(f)

except Exception as e:
    print("Errore lettura tokens.json:", e)
    sys.exit()

# =========================
# GESTIONE CLIENT
# =========================

def gestisci_client(conn, addr):

    print(f"[Thread] Nuovo client connesso: {addr}")

    temperature = []
    umidita = []

    invio_numero = 0
    start_time = time.time()

    identita_client = None
    cabina_client = None
    ponte_client = None
    mqtt_client = None

    buffer = ""

    while True:
        try:
            data = conn.recv(1024)

            if not data:
                print("Client disconnesso")
                break

            buffer += data.decode("utf-8")

            #  Processa tutti i messaggi completi nel buffer
            while "\n" in buffer:
                linea, buffer = buffer.split("\n", 1)
                linea = linea.strip()
                if not linea:
                    continue

                dato = json.loads(linea)

            print("Gateway IoT in ricezione e invio")

            # Inizializzazione MQTT al primo dato ricevuto
            if identita_client is None:

                identita_client = dato.get("identita")
                cabina_client = dato.get("cabina")
                ponte_client = dato.get("ponte")

                if identita_client not in tokens:
                    print(f"[Thread {addr}] ERRORE: nessun token trovato per {identita_client}")
                    break

                token = tokens[identita_client]

                mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

                try:
                    mqtt_client.username_pw_set(token)
                    mqtt_client.connect(BROKER, PORTA_BROKER)
                    mqtt_client.loop_start()

                    print(f"[Thread {addr}] MQTT connesso per dispositivo {identita_client}")

                except Exception as e:
                    print(f"[Thread {addr}] Errore connessione MQTT:", e)
                    break

            # Accumulo dati
            temperature.append(dato["temperature"])
            umidita.append(dato["humidity"])

            # Invio media ogni TEMPO_RILEVAZIONE secondi
            if time.time() - start_time >= TEMPO_RILEVAZIONE:

                media_t = round(
                    sum(temperature) / len(temperature),
                    NUMERO_DECIMALI
                )

                media_u = round(
                    sum(umidita) / len(umidita),
                    NUMERO_DECIMALI
                )

                invio_numero += 1

                dato_iot = {
                    "cabina": cabina_client,
                    "ponte": ponte_client,
                    "temperature": media_t,
                    "humidity": media_u,
                    "dataeora": int(time.time()),
                    "invionumero": invio_numero,
                    "identita": identita_client
                }

                dato_json = json.dumps(dato_iot)

                mqtt_client.publish(TOPIC, dato_json)

                print(f"Inviato a ThingsBoard ({identita_client}):", dato_iot)

                temperature = []
                umidita = []

                start_time = time.time()

        except Exception as e:
            print(f"[Thread {addr}] Errore:", e)
            break

    conn.close()

    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

    print(f"[Thread {addr}] Thread terminato per {identita_client}.")

# =========================
# SERVER SOCKET
# =========================

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    s.bind((IP_SERVER, PORTA_SERVER))

except PermissionError:

    print("Porta bloccata. Cambio porta automaticamente...")
    PORTA_SERVER = 6769

    try:
        s.bind((IP_SERVER, PORTA_SERVER))
        print("Nuova porta:", PORTA_SERVER)

    except Exception as e:
        print("Errore socket definitivo:", e)
        sys.exit()

except Exception as e:
    print("Errore bind:", e)
    sys.exit()

s.listen(10)
s.settimeout(1.0) # timeout per consentire di interrompere lo script 

print(f"Gateway IoT in attesa di connessioni su porta {PORTA_SERVER}...")

# =========================
# LOOP PRINCIPALE
# =========================

while True:

    try:
        conn, addr = s.accept()

        print(f"Nuova connessione da: {addr}")

        t = threading.Thread(
            target=gestisci_client,
            args=(conn, addr),
            daemon=True
        )

        t.start()

    except KeyboardInterrupt:

        print("\nGateway interrotto dall'utente.")
        s.close()
        break

    except Exception as e:

        print("Errore accettazione connessione:", e)