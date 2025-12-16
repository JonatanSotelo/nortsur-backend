# schemas.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# =========================
# CLIENTES
# =========================

class ClienteBase(BaseModel):
    numero_cliente: Optional[int] = None
    nombre: str
    direccion: Optional[str] = None
    barrio: Optional[str] = None
    telefono: Optional[str] = None
    vendedor: Optional[str] = None
    descuento_porcentaje: Optional[float] = None
    comentario: Optional[str] = None
    coordenadas: Optional[str] = None
    entrega_info: Optional[str] = None


class ClienteCreate(ClienteBase):
    """Datos de entrada para crear un cliente."""
    pass


class ClienteRead(ClienteBase):
    id: int
    deuda_centavos: int

    class Config:
        from_attributes = True  # Pydantic v2 (equivalente a orm_mode=True)


# =========================
# PRODUCTOS
# =========================
class ProductoRead(BaseModel):
    id: int
    codigo: str
    nombre: str
    categoria: Optional[str] = None
    presentacion: Optional[str] = None
    precio_centavos: int

    class Config:
        from_attributes = True


# =========================
# PEDIDOS
# =========================
class PedidoItemCreate(BaseModel):
    producto_id: int
    cantidad: int
    descripcion_extra: Optional[str] = None


class PedidoCreate(BaseModel):
    cliente_id: int
    canal: str
    observaciones: Optional[str] = None
    items: List[PedidoItemCreate]


class PedidoItemRead(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    precio_unitario_cent: int
    subtotal_cent: int
    descripcion_extra: Optional[str] = None

    class Config:
        from_attributes = True


class PedidoRead(BaseModel):
    id: int
    cliente_id: int
    fecha_creacion: datetime
    canal: str
    estado: str
    total_bruto_cent: int
    descuento_cliente: Optional[float] = None
    total_descuento_cent: int
    total_neto_cent: int
    observaciones: Optional[str] = None
    items: List[PedidoItemRead]

    class Config:
        from_attributes = True



# =========================
# INTEGRACIÓN BOT WHATSAPP
# =========================
class BotItemCreate(BaseModel):
    codigo: str
    cantidad: int


class BotPedidoFromWhatsApp(BaseModel):
    wa_phone: str                       # ej: "5491155732845"
    observaciones: Optional[str] = None
    items: List[BotItemCreate]          # productos por código


class BotPedidoResponse(BaseModel):
    ok: bool
    pedido_id: int
    cliente_id: int
    mensaje_respuesta: str
