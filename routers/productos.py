# routers/productos.py

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
import schemas
from database import get_db

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("/", response_model=list[schemas.ProductoRead])
def listar_productos(
    q: str | None = Query(default=None, description="Buscar por nombre (y opcionales si existen)"),
    solo_activos: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Producto)

    if solo_activos:
        query = query.filter(models.Producto.activo == True)  # noqa: E712

    if q:
        q2 = q.strip()
        like = f"%{q2}%"

        filtros = [models.Producto.nombre.ilike(like)]

        # Solo si el modelo tiene esos atributos (así no rompe)
        if hasattr(models.Producto, "descripcion"):
            filtros.append(models.Producto.descripcion.ilike(like))
        if hasattr(models.Producto, "codigo"):
            filtros.append(models.Producto.codigo.ilike(like))
        if hasattr(models.Producto, "sku"):
            filtros.append(models.Producto.sku.ilike(like))

        query = query.filter(or_(*filtros))

    return query.order_by(models.Producto.id.desc()).offset(offset).limit(limit).all()


@router.get("/{producto_id}", response_model=schemas.ProductoRead)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.patch("/{producto_id}", response_model=schemas.ProductoRead)
def editar_producto(
    producto_id: int,
    payload: schemas.ProductoUpdate,
    db: Session = Depends(get_db),
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    data = payload.dict(exclude_unset=True)

    # Regla: no permitir dejar nombre vacío si lo mandan
    if "nombre" in data and (data["nombre"] is None or data["nombre"].strip() == ""):
        raise HTTPException(status_code=422, detail="El nombre no puede estar vacío")

    for k, v in data.items():
        setattr(producto, k, v)

    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto



@router.patch("/{producto_id}/activar")
def activar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = True
    db.add(producto)
    db.commit()
    db.refresh(producto)

    return {"ok": True, "producto_id": producto_id, "activo": bool(producto.activo)}


@router.patch("/{producto_id}/desactivar")
def desactivar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = False
    db.add(producto)
    db.commit()
    db.refresh(producto)

    return {"ok": True, "producto_id": producto_id, "activo": bool(producto.activo)}

