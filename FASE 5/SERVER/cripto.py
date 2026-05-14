import base64

def criptazione(dato):
    return base64.b64encode(dato.encode()).decode()

def decriptazione(dato):
    return base64.b64decode(dato.encode()).decode()