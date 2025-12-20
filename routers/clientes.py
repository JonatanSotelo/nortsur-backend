# routers/clientes.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

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


@router.post("/", response_model=schemas.ClienteRead)
def crear_cliente(
    cliente_in: schemas.ClienteCreate,
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo cliente.
    - Normaliza el teléfono con normalize_phone.
    - Evita duplicar clientes con el mismo teléfono.
    - Si existe la columna numero_cliente, le asigna el siguiente número.
    """
    if not cliente_in.telefono:
        raise HTTPException(
            status_code=400,
            detail="El teléfono es obligatorio para crear un cliente que use el bot.",
        )

    telefono_normalizado = normalize_phone(cliente_in.telefono)

    # ¿Ya existe un cliente con ese teléfono?
    existente = (
        db.query(models.Cliente)
        .filter(models.Cliente.telefono == telefono_normalizado)
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un cliente con ese teléfono.",
        )

    # Calcular siguiente numero_cliente si la columna existe
    nuevo_numero = None
    if hasattr(models.Cliente, "numero_cliente"):
        max_num = db.query(func.max(models.Cliente.numero_cliente)).scalar()
        nuevo_numero = (max_num or 0) + 1

    cliente = models.Cliente(
        nombre=cliente_in.nombre,
        direccion=cliente_in.direccion,
        barrio=cliente_in.barrio,
        telefono=telefono_normalizado,
        descuento_porcentaje=cliente_in.descuento_porcentaje,
    )

    if nuevo_numero is not None:
        cliente.numero_cliente = nuevo_numero

    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


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
    - compara por los últimos 10 dígitos (según normalize_phone).
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
