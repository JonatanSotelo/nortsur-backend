from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
import schemas
from database import get_db

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=List[schemas.ProductoRead])
def listar_productos(
    q: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    GET /productos
    """
    query = db.query(models.Producto)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Producto.nombre.ilike(like),
                models.Producto.codigo.ilike(like),
                models.Producto.categoria.ilike(like),
            )
        )

    productos = (
        query.order_by(models.Producto.nombre)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return productos
