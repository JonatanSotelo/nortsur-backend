# NortSur - Sistema de Gestión de Pedidos

Sistema de gestión de pedidos desarrollado con FastAPI para NortSur.

## Características

- Gestión de clientes
- Gestión de productos
- Creación y seguimiento de pedidos
- Integración con bot de Telegram
- API REST completa
- Interfaz web para creación de pedidos

## Tecnologías

- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para base de datos
- **Pydantic**: Validación de datos
- **Jinja2**: Motor de plantillas
- **Uvicorn**: Servidor ASGI

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/JonatanSotelo/nortsur.git
cd nortsur
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar la base de datos (ver `database.py`)

4. Ejecutar la aplicación:
```bash
uvicorn main:app --reload
```

## Estructura del Proyecto

```
nortsur/
├── main.py              # Aplicación principal FastAPI
├── database.py          # Configuración de base de datos
├── models.py            # Modelos SQLAlchemy
├── schemas.py           # Esquemas Pydantic
├── routers/             # Endpoints de la API
│   ├── clientes.py
│   ├── productos.py
│   ├── pedidos.py
│   └── bot.py
├── services/            # Lógica de negocio
├── templates/           # Plantillas HTML
└── utils/               # Utilidades

```

## Endpoints Principales

- `GET /` - Interfaz web para crear pedidos
- `GET /health` - Health check
- `/api/clientes` - Gestión de clientes
- `/api/productos` - Gestión de productos
- `/api/pedidos` - Gestión de pedidos
- `/bot` - Endpoints del bot de Telegram

## Autor

JonatanSotelo

## Licencia

Este proyecto es privado.
