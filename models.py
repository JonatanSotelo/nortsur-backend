from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    BigInteger, Numeric, Text, CheckConstraint, Boolean
)
from sqlalchemy.orm import relationship

from database import Base  # 👈 IMPORTANTE: usamos el Base del database.py


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    numero_cliente = Column(Integer, index=True, nullable=True)
    nombre = Column(String, nullable=False)
    direccion = Column(String, nullable=True)
    barrio = Column(String, nullable=True)
    telefono = Column(String, nullable=True, index=True)
    vendedor = Column(String, nullable=True)
    descuento_porcentaje = Column(Numeric(5, 2), nullable=True)
    comentario = Column(Text, nullable=True)
    coordenadas = Column(String, nullable=True)
    deuda_centavos = Column(BigInteger, default=0, nullable=False)
    entrega_info = Column(Text, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    activo = Column(Boolean, default=True, nullable=False)
    actualizado_en = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    pedidos = relationship("Pedido", back_populates="cliente")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)
    nombre = Column(String, nullable=False)
    categoria = Column(String, nullable=True)
    presentacion = Column(String, nullable=True)
    precio_centavos = Column(BigInteger, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
    activo = Column(Boolean, default=True, nullable=False)
    actualizado_en = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    items = relationship("PedidoItem", back_populates="producto")


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow, nullable=False)
    canal = Column(String, nullable=False)  # 'whatsapp', 'web', 'manual', etc.
    estado = Column(String, nullable=False, default="pendiente")

    total_bruto_cent = Column(BigInteger, nullable=False, default=0)
    descuento_cliente = Column(Numeric(5, 2), nullable=True)
    total_descuento_cent = Column(BigInteger, nullable=False, default=0)
    total_neto_cent = Column(BigInteger, nullable=False, default=0)

    observaciones = Column(Text, nullable=True)
    origen_referencia = Column(String, nullable=True)

    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    cliente = relationship("Cliente", back_populates="pedidos")
    items = relationship("PedidoItem", back_populates="pedido", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "estado IN ('NUEVO','CONFIRMADO','ENTREGADO','CANCELADO')",
            name="ck_pedidos_estado",
        ),
    )

class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)

    cantidad = Column(Integer, nullable=False)
    precio_unitario_cent = Column(BigInteger, nullable=False)
    subtotal_cent = Column(BigInteger, nullable=False)

    descripcion_extra = Column(Text, nullable=True)

    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="items")
