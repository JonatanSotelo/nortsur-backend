# routers/pedidos.py

from __future__ import annotations

from typing import Optional

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
import schemas
from database import get_db
from services.pedidos_services import create_pedido

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


# ---------------------------------------------------------------------
# Estados válidos (alineado con el CHECK constraint en SQLite)
# ---------------------------------------------------------------------
ESTADOS_VALIDOS = {"NUEVO", "CONFIRMADO", "ENTREGADO", "CANCELADO"}

TRANSICIONES = {
    "NUEVO": {"CONFIRMADO", "CANCELADO"},
    "CONFIRMADO": {"ENTREGADO", "CANCELADO"},
    "ENTREGADO": set(),
    "CANCELADO": set(),
}


def normalizar_estado(valor: Optional[str]) -> str:
    """
    Normaliza estados entrantes para evitar fallos por CHECK constraint.
    - trim + upper
    - mapea legacy: 'pendiente' -> 'NUEVO'
    - default: NUEVO si viene None/vacío
    """
    if valor is None:
        return "NUEVO"
    s = str(valor).strip().upper()
    if s == "":
        return "NUEVO"
    if s == "PENDIENTE":
        return "NUEVO"
    return s


# ---------------------------------------------------------------------
# Helpers: observaciones + resumen (para WhatsApp / UI)
# ---------------------------------------------------------------------
def _money(cent: int | None) -> str:
    # 20700 -> "$20.700,00"
    pesos = (cent or 0) / 100
    s = f"{pesos:,.2f}"
    # swap separators (US -> AR)
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${s}"


def _append_obs(pedido: models.Pedido, texto: str) -> None:
    texto = (texto or "").strip()
    if not texto:
        return
    base = (pedido.observaciones or "").rstrip()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    linea = f"[{stamp}] {texto}"
    pedido.observaciones = (base + "\n" + linea).strip() if base else linea


def _build_resumen_texto(pedido: models.Pedido, db: Session) -> str:
    cliente = (
        db.query(models.Cliente)
        .filter(models.Cliente.id == pedido.cliente_id)
        .first()
    )
    nombre = (cliente.nombre if cliente else "Cliente")
    tel = (cliente.telefono if cliente and cliente.telefono else "")

    lines: list[str] = []
    lines.append(f"Pedido #{pedido.id} – {pedido.estado}")
    lines.append(f"Cliente: {nombre}" + (f" ({tel})" if tel else ""))
    lines.append("")

    items = (
        db.query(models.PedidoItem)
        .filter(models.PedidoItem.pedido_id == pedido.id)
        .all()
    )

    for it in items:
        prod = (
            db.query(models.Producto)
            .filter(models.Producto.id == it.producto_id)
            .first()
        )
        prod_nombre = prod.nombre if prod else f"Producto {it.producto_id}"

        lines.append(
            f"- {it.cantidad}x {prod_nombre} | {_money(it.precio_unitario_cent)} | Sub: {_money(it.subtotal_cent)}"
        )

    lines.append("")
    lines.append(f"Total: {_money(pedido.total_neto_cent)}")

    if pedido.observaciones:
        lines.append("")
        lines.append(f"Obs: {pedido.observaciones}")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------
# CRUD base
# ---------------------------------------------------------------------
@router.post("/", response_model=schemas.PedidoRead)
def crear_pedido(
    pedido_in: schemas.PedidoCreate,
    db: Session = Depends(get_db),
):
    return create_pedido(db, pedido_in)


@router.get("/", response_model=list[schemas.PedidoRead])
def listar_pedidos(
    q: str | None = Query(default=None, description="Buscar por cliente (nombre/teléfono)"),
    estado: str | None = Query(default=None),
    cliente_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Pedido)

    if cliente_id is not None:
        query = query.filter(models.Pedido.cliente_id == cliente_id)

    if estado:
        query = query.filter(models.Pedido.estado == estado.strip().upper())

    if q:
        like = f"%{q.strip()}%"
        query = (
            query.join(models.Cliente, models.Cliente.id == models.Pedido.cliente_id)
            .filter(
                or_(
                    models.Cliente.nombre.ilike(like),
                    models.Cliente.telefono.ilike(like),
                )
            )
        )

    return query.order_by(models.Pedido.id.desc()).offset(offset).limit(limit).all()


@router.get("/search", response_model=list[schemas.PedidoRead])
def buscar_pedidos_avanzado(
    q: str = Query(..., description="Buscar por cliente o producto"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    like = f"%{q.strip()}%"

    query = (
        db.query(models.Pedido)
        .join(models.Cliente, models.Cliente.id == models.Pedido.cliente_id)
        .join(models.PedidoItem, models.PedidoItem.pedido_id == models.Pedido.id)
        .join(models.Producto, models.Producto.id == models.PedidoItem.producto_id)
        .filter(
            or_(
                models.Cliente.nombre.ilike(like),
                models.Cliente.telefono.ilike(like),
                models.Producto.nombre.ilike(like),
            )
        )
        .distinct()
    )

    return query.order_by(models.Pedido.id.desc()).offset(offset).limit(limit).all()


@router.get("/estados")
def listar_estados():
    return ["NUEVO", "CONFIRMADO", "ENTREGADO", "CANCELADO"]


@router.get("/transiciones")
def listar_transiciones():
    return {k: sorted(list(v)) for k, v in TRANSICIONES.items()}


@router.get("/{pedido_id}", response_model=schemas.PedidoRead)
def obtener_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return pedido


@router.patch("/{pedido_id}", response_model=schemas.PedidoRead)
def editar_pedido(
    pedido_id: int,
    payload: schemas.PedidoUpdate,
    db: Session = Depends(get_db),
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # 🔒 Solo editable si está en NUEVO
    if (pedido.estado or "").strip().upper() != "NUEVO":
        raise HTTPException(status_code=409, detail="Solo se pueden modificar pedidos en estado NUEVO")

    if payload.observaciones is not None:
        pedido.observaciones = payload.observaciones

    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


# ---------------------------------------------------------------------
# Resumen listo para WhatsApp
# ---------------------------------------------------------------------
@router.get("/{pedido_id}/resumen")
def resumen_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    texto = _build_resumen_texto(pedido, db)
    return {"pedido_id": pedido.id, "texto": texto}


# ---------------------------------------------------------------------
# Cambios de estado (dos formas):
# A) Genérico PATCH /{id}/estado (para UI/admin)
# B) Acciones POST /confirmar /entregar /cancelar /reabrir (para bot)
# ---------------------------------------------------------------------
@router.patch("/{pedido_id}/estado", response_model=schemas.PedidoRead)
def cambiar_estado_pedido(
    pedido_id: int,
    payload: schemas.PedidoEstadoUpdate,
    db: Session = Depends(get_db),
):
    estado = normalizar_estado(payload.estado)

    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"Estado inválido: {estado!r}. Válidos: {sorted(ESTADOS_VALIDOS)}",
        )

    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    actual = (pedido.estado or "").strip().upper()
    permitidos = TRANSICIONES.get(actual)

    if permitidos is None:
        raise HTTPException(status_code=409, detail=f"Estado actual inválido en DB: {actual!r}")

    if estado not in permitidos:
        raise HTTPException(status_code=409, detail=f"Transición inválida: {actual} -> {estado}")

    pedido.estado = estado
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


@router.post("/{pedido_id}/confirmar")
def confirmar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        return {"ok": False, "error": "Pedido no encontrado", "pedido_id": pedido_id}

    actual = (pedido.estado or "").strip().upper()
    if "CONFIRMADO" not in TRANSICIONES.get(actual, set()):
        return {
            "ok": False,
            "error": f"Transición inválida: {actual} -> CONFIRMADO",
            "pedido_id": pedido.id,
            "estado_actual": actual,
            "permitidos": sorted(list(TRANSICIONES.get(actual, set()))),
        }

    pedido.estado = "CONFIRMADO"
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    resumen = _build_resumen_texto(pedido, db)
    return {"ok": True, "pedido_id": pedido.id, "estado": pedido.estado, "resumen": resumen, "pedido": pedido}


@router.post("/{pedido_id}/entregar")
def entregar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        return {"ok": False, "error": "Pedido no encontrado", "pedido_id": pedido_id}

    actual = (pedido.estado or "").strip().upper()
    if "ENTREGADO" not in TRANSICIONES.get(actual, set()):
        return {
            "ok": False,
            "error": f"Transición inválida: {actual} -> ENTREGADO",
            "pedido_id": pedido.id,
            "estado_actual": actual,
            "permitidos": sorted(list(TRANSICIONES.get(actual, set()))),
        }

    pedido.estado = "ENTREGADO"
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    resumen = _build_resumen_texto(pedido, db)
    return {"ok": True, "pedido_id": pedido.id, "estado": pedido.estado, "resumen": resumen}


@router.post("/{pedido_id}/cancelar")
def cancelar_pedido_accion(
    pedido_id: int,
    payload: schemas.PedidoCancelar | None = None,  # {"motivo": "..."}
    db: Session = Depends(get_db),
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        return {"ok": False, "error": "Pedido no encontrado", "pedido_id": pedido_id}

    actual = (pedido.estado or "").strip().upper()
    if "CANCELADO" not in TRANSICIONES.get(actual, set()):
        return {
            "ok": False,
            "error": f"Transición inválida: {actual} -> CANCELADO",
            "pedido_id": pedido.id,
            "estado_actual": actual,
            "permitidos": sorted(list(TRANSICIONES.get(actual, set()))),
        }

    motivo = ""
    if payload and getattr(payload, "motivo", None):
        motivo = (payload.motivo or "").strip()

    if motivo:
        _append_obs(pedido, f"[CANCELADO] {motivo}")
    else:
        _append_obs(pedido, "[CANCELADO]")

    pedido.estado = "CANCELADO"
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    resumen = _build_resumen_texto(pedido, db)
    return {"ok": True, "pedido_id": pedido.id, "estado": pedido.estado, "resumen": resumen}


@router.post("/{pedido_id}/reabrir")
def reabrir_pedido(
    pedido_id: int,
    payload: schemas.PedidoCancelar | None = None,  # reuse schema: {"motivo": "..."}
    db: Session = Depends(get_db),
):
    pedido = db.query(models.Pedido).filter(models.Pedido.id == pedido_id).first()
    if not pedido:
        return {"ok": False, "error": "Pedido no encontrado", "pedido_id": pedido_id}

    actual = (pedido.estado or "").strip().upper()
    if actual != "CANCELADO":
        return {
            "ok": False,
            "error": f"Solo se puede reabrir si está CANCELADO (actual: {actual})",
            "pedido_id": pedido.id,
            "estado_actual": actual,
        }

    motivo = ""
    if payload and getattr(payload, "motivo", None):
        motivo = (payload.motivo or "").strip()

    if motivo:
        _append_obs(pedido, f"[REABIERTO] {motivo}")
    else:
        _append_obs(pedido, "[REABIERTO]")

    pedido.estado = "NUEVO"
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    resumen = _build_resumen_texto(pedido, db)
    return {"ok": True, "pedido_id": pedido.id, "estado": pedido.estado, "resumen": resumen}

