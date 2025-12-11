# services/pedidos_services.py

from sqlalchemy.orm import Session
from fastapi import HTTPException

import models
import schemas


def create_pedido(db: Session, pedido_in: schemas.PedidoCreate) -> models.Pedido:
    cliente = (
        db.query(models.Cliente)
        .filter(models.Cliente.id == pedido_in.cliente_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    total_bruto = 0
    items_models: list[models.PedidoItem] = []

    for item_in in pedido_in.items:
        producto = (
            db.query(models.Producto)
            .filter(models.Producto.id == item_in.producto_id)
            .first()
        )
        if not producto:
            raise HTTPException(
                status_code=404,
                detail=f"Producto id={item_in.producto_id} no encontrado",
            )

        precio_unitario = producto.precio_centavos
        subtotal = precio_unitario * item_in.cantidad
        total_bruto += subtotal

        item_model = models.PedidoItem(
            producto_id=producto.id,
            cantidad=item_in.cantidad,
            precio_unitario_cent=precio_unitario,
            subtotal_cent=subtotal,
            descripcion_extra=item_in.descripcion_extra,
        )
        items_models.append(item_model)

    descuento_porcentaje = float(cliente.descuento_porcentaje or 0)
    total_descuento = int(total_bruto * descuento_porcentaje / 100)
    total_neto = total_bruto - total_descuento

    pedido = models.Pedido(
        cliente_id=cliente.id,
        canal=pedido_in.canal,
        estado="pendiente",
        total_bruto_cent=total_bruto,
        descuento_cliente=descuento_porcentaje or None,
        total_descuento_cent=total_descuento,
        total_neto_cent=total_neto,
        observaciones=pedido_in.observaciones,
        items=items_models,
    )

    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    return pedido
