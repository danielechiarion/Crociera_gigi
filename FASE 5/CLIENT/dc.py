import socket      # libreria per creare socket tcp/ip
import json        # libreria per lavorare con file json
import time        # libreria gestione tempo
import random      # libreria numeri casuali
import os          # libreria gestione file/cartelle
import sys         # libreria gestione sistema
                    # sys.argv: lista argomenti passati da riga di comando
                    # sys.argv[0] = nome script
                    # sys.argv[1] = primo argomento (identità cabina)

# =========================
# LETTURA IDENTITÀ DA RIGA DI COMANDO
# =========================
# Ogni cabina si distingue dall'identità passata come argomento:
#   python dc.py DC-001
#   python dc.py DC-002
#   python dc.py DC-003
# Lo script è uno solo; cambia solo il parametro di lancio.

if len(sys.argv) < 2:
    print("Uso: python dc.py <identita>")
    print("Esempio: python dc.py DC-001")
    sys.exit()

# variabile IDENTITA
# identificativo univoco di questa istanza (es. "DC-001")
# tipo: stringa
IDENTITA = sys.argv[1]

# =========================
# CARICAMENTO CONFIGURAZIONE
# =========================
# Un solo file da.json contiene i parametri di tutte le cabine.
# La chiave di accesso è l'identità passata da riga di comando.

CONFIG_FILE = "Configurazione/da.json"

if not os.path.exists(CONFIG_FILE):
    print(f"ERRORE: file {CONFIG_FILE} non trovato.")
    sys.exit()

try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception as e:
    print("ERRORE lettura da.json:", e)
    sys.exit()

# controllo che l'identità richiesta esista nel file
if IDENTITA not in config:
    print(f"ERRORE: identità '{IDENTITA}' non trovata in {CONFIG_FILE}")
    print("Identità disponibili:", list(config.keys()))
    sys.exit()

# variabile parametri
# contiene i parametri specifici di questa cabina
# tipo: dizionario
parametri = config[IDENTITA]

try:
    IP     = parametri["IP"]
    PORTA  = parametri["porta"]
    CABINA = parametri["cabina"]
    PONTE  = parametri["ponte"]
except KeyError as e:
    print(f"ERRORE: chiave mancante in da.json per {IDENTITA}:", e)
    sys.exit()

print(f"Dispositivo: {IDENTITA} | Cabina {CABINA} | Ponte {PONTE}")

# =========================
# CREAZIONE SOCKET
# =========================

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.connect((IP, PORTA))
except Exception as e:
    print("ERRORE connessione al gateway:", e)
    sys.exit()

print(f"Connesso al Gateway IoT ({IP}:{PORTA})")

# =========================
# LOOP INVIO DATI
# =========================

while True:

    try:

        temperatura = round(random.uniform(18.0, 22.0), 2)
        umidita     = round(random.uniform(60.0, 70.0), 2)

        # variabile dato
        # il campo "identita" è fondamentale:
        # il gateway lo usa per scegliere il token MQTT corretto
        # e scrivere sui dispositivo ThingsBoard della cabina giusta
        dato = {
            "identita":   IDENTITA,
            "cabina":     CABINA,
            "ponte":      PONTE,
            "temperatura": temperatura,
            "umidita":    umidita
        }

        dato_json = json.dumps(dato)

        print(f"[{IDENTITA}] Dato inviato:", dato)

        s.sendall(dato_json.encode("utf-8"))

        time.sleep(2)

    except KeyboardInterrupt:
        print(f"\n[{IDENTITA}] Chiusura client...")
        s.close()
        break

    except Exception as e:
        print(f"[{IDENTITA}] ERRORE durante invio dati:", e)
        s.close()
        break
