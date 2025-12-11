# utils/telefonos.py

def normalize_phone(phone: str) -> str:
    """
    Normaliza teléfonos a solo dígitos y se queda con los últimos 10,
    que suele ser lo más estable (ej: 11XXXXXXXX o 3XXXXXXXXX).
    """
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) > 10:
        return digits[-10:]
    return digits
