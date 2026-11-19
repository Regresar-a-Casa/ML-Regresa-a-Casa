"""Utilidades criptográficas: derivación de claves (PBKDF2-HMAC-SHA256) y cifrado Fernet.

La librería ``cryptography`` se importa de forma perezosa para que el resto del sistema
(modelo, mapas) funcione aunque no esté instalada.
"""
import base64

from .config import ITERACIONES_KDF


def _cripto():
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError:
        raise ImportError("Falta la librería 'cryptography'. Instálala con:\n"
                          "python -m pip install cryptography")
    return Fernet, InvalidToken, hashes, PBKDF2HMAC


def fernet():
    """Clase ``Fernet``."""
    return _cripto()[0]


def token_invalido():
    """Excepción ``InvalidToken`` (contraseña o folio incorrecto)."""
    return _cripto()[1]


def derivar_clave(contrasena, sal):
    """Deriva un objeto Fernet a partir de una contraseña y una sal de 16 bytes."""
    Fernet, _, hashes, PBKDF2HMAC = _cripto()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=ITERACIONES_KDF)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(contrasena.encode("utf-8"))))
