# routers/clientes.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
import schemas
from database import get_db
from utils.telefonos import normalize_phone

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("/", response_model=List[schemas.ClienteRead])
def listar_clientes(
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(models.Cliente)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Cliente.nombre.ilike(like),
                models.Cliente.direccion.ilike(like),
                models.Cliente.barrio.ilike(like),
                models.Cliente.telefono.ilike(like),
            )
        )

    clientes = (
        query.order_by(models.Cliente.nombre)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return clientes


@router.get("/{cliente_id}", response_model=schemas.ClienteRead)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = (
        db.query(models.Cliente)
        .filter(models.Cliente.id == cliente_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/by-phone/{telefono}", response_model=schemas.ClienteRead)
def obtener_cliente_por_telefono(telefono: str, db: Session = Depends(get_db)):
    """
    Busca el cliente por teléfono usando normalización:
    - quita espacios, +, -, etc.
    - compara por los últimos 10 dígitos.
    Esto hace match aunque WhatsApp traiga +54911... y en la planilla esté 11-XXXX-XXXX.
    """
    objetivo = normalize_phone(telefono)

    clientes = db.query(models.Cliente).all()
    for c in clientes:
        if not c.telefono:
            continue
        if normalize_phone(c.telefono) == objetivo:
            return c

    raise HTTPException(
        status_code=404,
        detail="Cliente no encontrado para ese teléfono",
    )
