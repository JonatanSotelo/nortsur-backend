# routers/pedidos.py

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from services.pedidos_services import create_pedido

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("", response_model=schemas.PedidoRead)
def crear_pedido(
    pedido_in: schemas.PedidoCreate,
    db: Session = Depends(get_db),
):
    pedido = create_pedido(db, pedido_in)
    return pedido


@router.get("", response_model=List[schemas.PedidoRead])
def listar_pedidos(
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    pedidos = (
        db.query(models.Pedido)
        .order_by(models.Pedido.fecha_creacion.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return pedidos
