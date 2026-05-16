import socket
import json
import time
import sys
import threading
import paho.mqtt.client as mqtt
import cripto

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
    mqtt_client = None

    while True:

        try:
            data = conn.recv(1024)

            if not data:
                print(f"[Thread] Client {addr} disconnesso.")
                break

            dato = json.loads(data.decode())

            print(f"[Thread {addr}] Dato ricevuto:", dato)

            # Inizializzazione MQTT al primo dato ricevuto
            if identita_client is None:

                identita_client = dato.get("identita")

                if identita_client not in tokens:
                    print(f"[Thread {addr}] ERRORE: nessun token trovato per {identita_client}")
                    break

                token = tokens[identita_client]

                mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

                try:
                    mqtt_client.username_pw_set(token)
                    mqtt_client.connect(BROKER, PORTA_BROKER)

                    print(f"[Thread {addr}] MQTT connesso per dispositivo {identita_client}")

                except Exception as e:
                    print(f"[Thread {addr}] Errore connessione MQTT:", e)
                    break

            # Accumulo dati
            temperature.append(dato["temperatura"])
            umidita.append(dato["umidita"])

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
                    "temperaturam": media_t,
                    "umiditam": media_u,
                    "dataeora": int(time.time()),
                    "invionumero": invio_numero,
                    "identita": identita_client
                }

                dato_json = json.dumps(dato_iot)

                # Cifratura mantenuta per eventuali utilizzi futuri
                dato_cripto = cripto.criptazione(dato_json)

                mqtt_client.publish(TOPIC, dato_json)

                print(f"[Thread {addr}] Inviato a ThingsBoard ({identita_client}):", dato_iot)

                temperature = []
                umidita = []

                start_time = time.time()

        except Exception as e:
            print(f"[Thread {addr}] Errore:", e)
            break

    conn.close()

    if mqtt_client:
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