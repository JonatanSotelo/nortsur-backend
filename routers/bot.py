# routers/bot.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from services.pedidos_services import create_pedido
from utils.telefonos import normalize_phone

router = APIRouter(prefix="/bot", tags=["bot"])


def find_cliente_by_phone(db: Session, wa_phone: str) -> models.Cliente | None:
    """
    Busca el cliente comparando por los últimos 10 dígitos del teléfono.
    Usa la misma lógica que /clientes/by-phone.
    """
    objetivo = normalize_phone(wa_phone)
    clientes = db.query(models.Cliente).all()
    for c in clientes:
        if not c.telefono:
            continue
        if normalize_phone(c.telefono) == objetivo:
            return c
    return None


@router.get("/productos/buscar")
def bot_buscar_productos(texto: str, db: Session = Depends(get_db)):
    """
    Devuelve hasta 5 productos que matcheen por nombre/presentación/categoría.
    Lo vamos a usar desde el bot para 'pedido por descripción'.
    """
    q = (texto or "").strip()
    if not q:
        return []

    like = f"%{q}%"

    productos = (
        db.query(models.Producto)
        .filter(
            or_(
                models.Producto.nombre.ilike(like),
                models.Producto.presentacion.ilike(like),
                models.Producto.categoria.ilike(like),
            )
        )
        .order_by(models.Producto.nombre)
        .limit(5)
        .all()
    )

    return [
        {
            "codigo": p.codigo,
            "nombre": p.nombre,
            "presentacion": p.presentacion,
            "precio_centavos": p.precio_centavos,
        }
        for p in productos
    ]


@router.post("/pedidos/from-whatsapp", response_model=schemas.BotPedidoResponse)
def crear_pedido_from_whatsapp(
    data: schemas.BotPedidoFromWhatsApp,
    db: Session = Depends(get_db),
):
    """
    Endpoint pensado para que lo llame el BOT de WhatsApp.

    Recibe:
    - wa_phone: número de WhatsApp del cliente (ej: "5491155732845")
    - observaciones: texto libre
    - items: lista de {codigo, cantidad}

    Devuelve:
    - ok, pedido_id, cliente_id, mensaje_respuesta (texto para enviar al cliente)
    """
    # 1) Buscar cliente por teléfono
    cliente = find_cliente_by_phone(db, data.wa_phone)
    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado para ese teléfono",
        )

    # 2) Convertir items por código → PedidoItemCreate (producto_id + cantidad)
    items_in: List[schemas.PedidoItemCreate] = []

    for item in data.items:
        producto = (
            db.query(models.Producto)
            .filter(models.Producto.codigo == item.codigo)
            .first()
        )
        if not producto:
            raise HTTPException(
                status_code=404,
                detail=f"Producto con código '{item.codigo}' no encontrado",
            )

        items_in.append(
            schemas.PedidoItemCreate(
                producto_id=producto.id,
                cantidad=item.cantidad,
                descripcion_extra=None,
            )
        )

    if not items_in:
        raise HTTPException(status_code=400, detail="El pedido no tiene ítems válidos")

    # 3) Crear Pedido usando el servicio existente
    pedido_in = schemas.PedidoCreate(
        cliente_id=cliente.id,
        canal="whatsapp",
        observaciones=data.observaciones,
        items=items_in,
    )

    pedido = create_pedido(db, pedido_in)

    # 4) Armar texto de respuesta para el cliente
    lineas: list[str] = []
    lineas.append(f"Hola {cliente.nombre}, tu pedido #{pedido.id} fue registrado ✅")
    lineas.append("")
    lineas.append("Detalle:")

    # Como 'pedido' es un modelo SQLAlchemy, podemos acceder a las relaciones
    for it in pedido.items:
        producto = it.producto
        desc_prod = (
            f"{producto.codigo} {producto.nombre}"
            if producto
            else f"ID {it.producto_id}"
        )
        linea = f"- x{it.cantidad} {desc_prod} = ${it.subtotal_cent/100:.2f}"
        lineas.append(linea)

    lineas.append("")
    lineas.append(f"TOTAL: ${pedido.total_neto_cent/100:.2f}")

    mensaje = "\n".join(lineas)

    return schemas.BotPedidoResponse(
        ok=True,
        pedido_id=pedido.id,
        cliente_id=cliente.id,
        mensaje_respuesta=mensaje,
    )
