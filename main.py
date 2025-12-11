# main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import models
from database import engine
from routers import clientes, pedidos, productos, bot

# Crear tablas si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nortsur Pedidos")

# CORS abierto para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Montamos routers
app.include_router(clientes.router)
app.include_router(pedidos.router)
app.include_router(productos.router)  # 👈 importante
app.include_router(bot.router)  # 👈 NUEVO

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Página mínima para crear pedidos (pedido_simple.html).
    """
    return templates.TemplateResponse(
        "pedido_simple.html",
        {"request": request},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
