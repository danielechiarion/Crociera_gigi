import socket      # libreria per creare socket tcp/ip
                    # funzione principale usata: socket.socket()
                    # parametri:
                    # - socket.AF_INET  -> usa indirizzi ipv4
                    # - socket.SOCK_STREAM -> usa protocollo tcp
                    # restituisce:
                    # - un oggetto socket

import json        # libreria per lavorare con file json
                    # funzione json.load(file)
                    # parametri:
                    # - file aperto
                    # restituisce:
                    # - dizionario python
                    #
                    # funzione json.loads(stringa)
                    # parametri:
                    # - stringa json
                    # restituisce:
                    # - dizionario python
                    #
                    # funzione json.dumps(oggetto)
                    # parametri:
                    # - dizionario python
                    # restituisce:
                    # - stringa json

import time        # libreria gestione tempo
                    # funzione time.time()
                    # parametri:
                    # - nessuno
                    # restituisce:
                    # - timestamp corrente
                    #
                    # funzione time.sleep(secondi)
                    # parametri:
                    # - secondi pausa
                    # restituisce:
                    # - niente

import sys         # libreria gestione sistema
                    # funzione sys.exit()
                    # parametri:
                    # - opzionale codice uscita
                    # restituisce:
                    # - niente, termina programma

import threading   # libreria per gestione thread paralleli
                    # funzione threading.Thread()
                    # parametri:
                    # - target: funzione da eseguire nel thread
                    # - args: argomenti della funzione
                    # restituisce:
                    # - oggetto Thread

import paho.mqtt.client as mqtt
                    # libreria mqtt
                    # funzione mqtt.Client()
                    # parametri:
                    # - versione callback api
                    # restituisce:
                    # - client mqtt

import cripto      # libreria personalizzata per cifrare dati
                    # funzione cripto.criptazione(dato)
                    # parametri:
                    # - stringa da cifrare
                    # restituisce:
                    # - stringa cifrata

# =========================
# CARICAMENTO CONFIG
# =========================

try:

    # funzione open()
    # apre file json
    # parametri:
    # - percorso file
    # - modalità apertura
    # - encoding
    # restituisce:
    # - oggetto file

    with open("Configurazione/parametri.json", "r", encoding="utf-8") as file:

        # funzione json.load()
        # converte json in dizionario
        # parametri:
        # - file aperto
        # restituisce:
        # - dizionario python

        parametri = json.load(file)

        # variabile parametri
        # contiene tutti i dati letti dal json
        # tipo:
        # - dizionario

except Exception as e:

    print("Errore lettura parametri:", e)
    sys.exit()

# variabile TEMPO_RILEVAZIONE
# tempo in secondi per calcolare le medie
# tipo: intero
TEMPO_RILEVAZIONE = parametri["TEMPO_RILEVAZIONE"]

# variabile NUMERO_DECIMALI
# numero cifre decimali per arrotondamento
# tipo: intero
NUMERO_DECIMALI = parametri["N_DECIMALI"]

# variabile IP_SERVER
# indirizzo ip server socket
# tipo: stringa
IP_SERVER = parametri["IP_SERVER"]

# variabile PORTA_SERVER
# porta server socket
# tipo: intero
PORTA_SERVER = parametri["PORTA_SERVER"]

# variabile TOPIC
# topic mqtt per pubblicazione dati
# tipo: stringa
TOPIC = parametri["TOPIC"]

# variabile BROKER
# indirizzo ip o hostname del broker mqtt
# tipo: stringa
BROKER = parametri["BROKER"]

# variabile PORTA_BROKER
# porta del broker mqtt
# tipo: intero
PORTA_BROKER = parametri["PORTA_BROKER"]

# =========================
# CARICAMENTO TOKENS
# =========================
# La mappa token è ora indicizzata per IDENTITA del dispositivo (DC-001, DC-002, DC-003)
# e non più per identità del gateway.
# Ogni cabina ha il proprio token ThingsBoard: il gateway sceglie
# il token corretto in base al campo "identita" ricevuto nel dato.

try:

    with open("Configurazione/tokens.json", "r", encoding="utf-8") as f:

        # variabile tokens
        # dizionario { identita_dispositivo -> token_thingsboard }
        # tipo: dizionario stringa->stringa
        tokens = json.load(f)

except Exception as e:

    print("Errore lettura tokens.json:", e)
    sys.exit()

# =========================
# FUNZIONE GESTIONE CLIENT
# =========================

def gestisci_client(conn, addr):

    # funzione gestisci_client()
    # gestisce un singolo client dc.py in un thread dedicato
    # parametri:
    # - conn: oggetto connessione socket del client
    # - addr: indirizzo ip e porta del client
    # restituisce:
    # - niente

    print(f"[Thread] Nuovo client connesso: {addr}")

    # variabile temperature
    # lista temperature ricevute in finestra temporale
    # tipo: lista float
    temperature = []

    # variabile umidita
    # lista umidità ricevute in finestra temporale
    # tipo: lista float
    umidita = []

    # variabile invio_numero
    # contatore progressivo degli invii mqtt
    # tipo: intero
    invio_numero = 0

    # variabile start_time
    # timestamp inizio finestra di rilevazione
    # tipo: float
    start_time = time.time()

    # variabile identita_client
    # identità del dispositivo ricevuta dal primo dato
    # tipo: stringa o None
    identita_client = None

    # variabile mqtt_client
    # client mqtt dedicato a questo dispositivo
    # tipo: oggetto mqtt.Client o None
    mqtt_client = None

    while True:

        try:

            # funzione recv()
            # riceve dati dalla socket
            # parametri:
            # - numero massimo byte da ricevere
            # restituisce:
            # - bytes ricevuti

            data = conn.recv(1024)

            # variabile data
            # contiene i byte ricevuti dal client

            if not data:

                # connessione chiusa dal client
                print(f"[Thread] Client {addr} disconnesso.")
                break

            # funzione decode()
            # converte bytes in stringa utf-8
            # parametri:
            # - nessuno (usa default utf-8)
            # restituisce:
            # - stringa

            # funzione json.loads()
            # converte stringa json in dizionario
            # parametri:
            # - stringa json
            # restituisce:
            # - dizionario python

            dato = json.loads(data.decode())

            # variabile dato
            # contiene i dati sensore ricevuti dal dc.py
            # struttura attesa:
            # {
            #   "identita": "DC-001",
            #   "cabina": 1,
            #   "ponte": 1,
            #   "temperatura": 20.5,
            #   "umidita": 65.3
            # }

            print(f"[Thread {addr}] Dato ricevuto:", dato)

            # =========================
            # INIZIALIZZAZIONE MQTT PER QUESTO DISPOSITIVO
            # =========================
            # Al primo dato ricevuto, legge l'identità del dispositivo
            # e crea un client mqtt con il token corrispondente.
            # Questo garantisce che ogni cabina scriva sul proprio
            # dispositivo ThingsBoard.

            if identita_client is None:

                # variabile identita_client
                # salva l'identità del dispositivo per tutto il ciclo di vita del thread
                identita_client = dato.get("identita")

                # controllo token disponibile per questa identità
                if identita_client not in tokens:

                    print(f"[Thread {addr}] ERRORE: nessun token trovato per {identita_client}")
                    break

                # variabile token
                # token thingsboard associato a questo dispositivo
                # tipo: stringa
                token = tokens[identita_client]

                # creazione client mqtt dedicato al dispositivo
                # funzione mqtt.Client()
                # parametri:
                # - mqtt.CallbackAPIVersion.VERSION2
                # restituisce:
                # - oggetto client mqtt
                mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

                try:

                    # funzione username_pw_set()
                    # imposta token come username (autenticazione thingsboard)
                    # parametri:
                    # - username: token del dispositivo
                    # restituisce:
                    # - niente
                    mqtt_client.username_pw_set(token)

                    # funzione connect()
                    # connette client mqtt al broker
                    # parametri:
                    # - broker: hostname o ip
                    # - porta: intero
                    # restituisce:
                    # - codice stato connessione
                    mqtt_client.connect(BROKER, PORTA_BROKER)

                    print(f"[Thread {addr}] MQTT connesso per dispositivo {identita_client}")

                except Exception as e:

                    print(f"[Thread {addr}] Errore connessione MQTT per {identita_client}:", e)
                    break

            # =========================
            # ACCUMULO DATI
            # =========================

            # funzione append()
            # aggiunge valore alla lista
            # parametri:
            # - valore da aggiungere
            # restituisce:
            # - niente

            temperature.append(dato["temperatura"])
            umidita.append(dato["umidita"])

            # =========================
            # CONTROLLO FINESTRA TEMPORALE
            # =========================

            if time.time() - start_time >= TEMPO_RILEVAZIONE:

                # funzione sum()
                # somma tutti gli elementi della lista
                # parametri:
                # - lista di numeri
                # restituisce:
                # - somma totale

                # funzione len()
                # restituisce numero di elementi
                # parametri:
                # - lista
                # restituisce:
                # - intero

                # funzione round()
                # arrotonda al numero di decimali configurato
                # parametri:
                # - numero
                # - cifre decimali
                # restituisce:
                # - numero arrotondato

                media_t = round(sum(temperature) / len(temperature), NUMERO_DECIMALI)

                # variabile media_t
                # contiene media delle temperature nell'intervallo
                # tipo: float

                media_u = round(sum(umidita) / len(umidita), NUMERO_DECIMALI)

                # variabile media_u
                # contiene media delle umidità nell'intervallo
                # tipo: float

                invio_numero += 1

                # variabile dato_iot
                # dizionario con dati aggregati pronti per ThingsBoard
                # la struttura non include più "cabina" e "ponte" come campi separati:
                # ThingsBoard identifica già il dispositivo tramite il token MQTT.
                # I campi rimangono come telemetria informativa.
                dato_iot = {
                    "temperaturam": media_t,
                    "umiditam": media_u,
                    "dataeora": int(time.time()),
                    "invionumero": invio_numero,
                    "identita": identita_client
                }

                # funzione json.dumps()
                # converte dizionario in stringa json
                # parametri:
                # - dizionario
                # restituisce:
                # - stringa json

                dato_json = json.dumps(dato_iot)

                # variabile dato_json
                # contiene json da inviare via mqtt
                # tipo: stringa

                # funzione cripto.criptazione()
                # cifra il dato json
                # parametri:
                # - stringa json
                # restituisce:
                # - stringa cifrata

                dato_cripto = cripto.criptazione(dato_json)

                # variabile dato_cripto
                # contiene dati cifrati (non inviati in questa versione, conservato per logging)
                # tipo: stringa

                # funzione publish()
                # pubblica messaggio mqtt sul topic configurato
                # il client mqtt usa già il token del dispositivo corretto
                # quindi ThingsBoard assegna i dati alla cabina giusta
                # parametri:
                # - topic: stringa
                # - payload: stringa json
                # restituisce:
                # - MQTTMessageInfo

                mqtt_client.publish(TOPIC, dato_json)

                print(f"[Thread {addr}] Inviato a ThingsBoard ({identita_client}):", dato_iot)

                # reset liste per prossima finestra temporale
                temperature = []
                umidita = []

                # reset timer
                start_time = time.time()

        except Exception as e:

            print(f"[Thread {addr}] Errore:", e)
            break

    # chiusura connessione socket del client
    conn.close()

    # chiusura client mqtt se aperto
    if mqtt_client:
        mqtt_client.disconnect()

    print(f"[Thread {addr}] Thread terminato per {identita_client}.")

# =========================
# SOCKET SERVER PRINCIPALE
# =========================

# funzione socket.socket()
# crea socket tcp server
# parametri:
# - socket.AF_INET
# - socket.SOCK_STREAM
# restituisce:
# - oggetto socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# variabile s
# contiene socket server principale

# funzione setsockopt()
# modifica opzioni socket
# parametri:
# - livello protocollo
# - opzione SO_REUSEADDR: permette riuso immediato della porta
# - valore 1: abilita opzione
# restituisce:
# - niente

s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:

    # funzione bind()
    # collega socket a ip e porta
    # parametri:
    # - tupla(ip, porta)
    # restituisce:
    # - niente

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

# funzione listen()
# mette server in ascolto
# parametri:
# - backlog: numero massimo di connessioni in coda (10 = tutti i client previsti + margine)
# restituisce:
# - niente

s.listen(10)

print(f"Gateway IoT in attesa di connessioni su porta {PORTA_SERVER}...")

# =========================
# LOOP ACCETTAZIONE CLIENT
# =========================
# Il gateway ora accetta connessioni multiple in loop infinito.
# Ogni client (dc.py) viene gestito in un thread separato,
# così le cabine inviano dati in parallelo senza bloccarsi a vicenda.

while True:

    try:

        # funzione accept()
        # accetta nuova connessione in arrivo
        # parametri:
        # - nessuno
        # restituisce:
        # - conn: oggetto connessione del client
        # - addr: tupla (ip, porta) del client

        conn, addr = s.accept()

        # variabile conn
        # contiene connessione socket del nuovo client

        # variabile addr
        # contiene indirizzo del nuovo client

        print(f"Nuova connessione da: {addr}")

        # funzione threading.Thread()
        # crea un nuovo thread per gestire il client
        # parametri:
        # - target: funzione da eseguire (gestisci_client)
        # - args: argomenti passati alla funzione
        # - daemon: True = il thread termina quando termina il programma principale
        # restituisce:
        # - oggetto Thread

        t = threading.Thread(target=gestisci_client, args=(conn, addr), daemon=True)

        # variabile t
        # contiene il thread appena creato

        # funzione start()
        # avvia il thread
        # parametri:
        # - nessuno
        # restituisce:
        # - niente

        t.start()

    except KeyboardInterrupt:

        print("\nGateway interrotto dall'utente.")
        s.close()
        break

    except Exception as e:

        print("Errore accettazione connessione:", e)
