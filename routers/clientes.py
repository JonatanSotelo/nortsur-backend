# routers/clientes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

import models
import schemas
from database import get_db
from utils.telefonos import normalize_phone

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("/", response_model=list[schemas.ClienteRead])
def listar_clientes(
    q: str | None = Query(default=None, description="Buscar por nombre o teléfono"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Cliente)

    if q:
        q2 = q.strip()
        like = f"%{q2}%"
        query = query.filter(
            or_(
                models.Cliente.nombre.ilike(like),
                models.Cliente.telefono.ilike(like),
            )
        )

    return query.order_by(models.Cliente.id.desc()).offset(offset).limit(limit).all()


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

    existente = (
        db.query(models.Cliente)
        .filter(models.Cliente.telefono == telefono_normalizado)
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un cliente con ese teléfono.")

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
        # si tu schema trae más campos, acá los sumamos (vendedor, comentario, etc.)
    )

    if nuevo_numero is not None:
        cliente.numero_cliente = nuevo_numero

    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get("/by-phone/{telefono}", response_model=schemas.ClienteRead)
def obtener_cliente_por_telefono(telefono: str, db: Session = Depends(get_db)):
    """
    Busca el cliente por teléfono usando normalización:
    - quita espacios, +, -, etc.
    - compara por los últimos 10 dígitos (según normalize_phone).
    """
    objetivo = normalize_phone(telefono)

    clientes = db.query(models.Cliente).all()
    for c in clientes:
        if not c.telefono:
            continue
        if normalize_phone(c.telefono) == objetivo:
            return c

    raise HTTPException(status_code=404, detail="Cliente no encontrado para ese teléfono")


@router.get("/{cliente_id}", response_model=schemas.ClienteRead)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.patch("/{cliente_id}", response_model=schemas.ClienteRead)
def editar_cliente(
    cliente_id: int,
    payload: schemas.ClienteUpdate,
    db: Session = Depends(get_db),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Pydantic v2
    data = payload.model_dump(exclude_unset=True)

    # Validación mínima: si mandan nombre, que no sea vacío
    if "nombre" in data and (data["nombre"] is None or str(data["nombre"]).strip() == ""):
        raise HTTPException(status_code=422, detail="El nombre no puede estar vacío")

    for k, v in data.items():
        setattr(cliente, k, v)

    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.patch("/{cliente_id}/activar")
def activar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente.activo = True
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return {"ok": True, "cliente_id": cliente_id, "activo": bool(cliente.activo)}


@router.patch("/{cliente_id}/desactivar")
def desactivar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente.activo = False
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    return {"ok": True, "cliente_id": cliente_id, "activo": bool(cliente.activo)}

