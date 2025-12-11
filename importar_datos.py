# importar_datos.py
import csv

from database import SessionLocal, engine
import models

# Aseguramos tablas
models.Base.metadata.create_all(bind=engine)


def safe_int(value: str | None) -> int | None:
    """
    Intenta convertir a int; si no puede (texto, vacío, etc.), devuelve None.
    """
    if value is None:
        return None
    txt = str(value).strip()
    if not txt:
        return None
    try:
        return int(txt)
    except ValueError:
        return None


def to_centavos(value: str | None) -> int:
    """
    Convierte un string numérico (con coma o punto) a centavos (int).
    Si no puede convertir, devuelve 0.
    """
    if value is None:
        return 0
    txt = str(value).strip()
    if not txt:
        return 0
    # Formato tipo '1.234,56' → '1234.56'
    txt = txt.replace(".", "").replace(",", ".")
    try:
        return int(float(txt) * 100)
    except ValueError:
        return 0


def to_descuento(value: str | None) -> float | None:
    """
    Convierte '10', '10%', ' 10,5 ' a float.
    Si el valor es 'SI', 'NO' u otro texto sin números, devuelve None.
    """
    if value is None:
        return None
    txt = str(value).strip()
    if not txt:
        return None

    # Si no tiene ningún dígito, lo tratamos como bandera (SI/NO) y no como porcentaje numérico
    if not any(ch.isdigit() for ch in txt):
        return None

    txt = txt.replace("%", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def get_dict_reader(csv_path: str):
    """
    Abre el CSV, detecta el delimitador (; , o TAB) y devuelve un DictReader.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";, \t")
        except csv.Error:
            dialect = csv.excel  # por defecto, coma

        reader = csv.DictReader(f, dialect=dialect)
        for row in reader:
            yield row


def importar_clientes(csv_path: str = "clientes_nortsur.csv"):
    """
    Espera columnas:
    id, numero_cliente, nombre, direccion, barrio, telefono,
    vendedor, tiene_descuento, comentario_adicional,
    deuda, tipo_entrega, coordenadas_lat, coordenadas_lng
    """
    db = SessionLocal()
    try:
        for idx, row in enumerate(get_dict_reader(csv_path), start=1):
            raw_num = row.get("numero_cliente")
            raw_desc = row.get("tiene_descuento")
            raw_deuda = row.get("deuda")
            lat = row.get("coordenadas_lat")
            lng = row.get("coordenadas_lng")

            # Armamos un solo campo de coordenadas "lat,lng"
            coords = None
            if lat or lng:
                lat_txt = (lat or "").strip()
                lng_txt = (lng or "").strip()
                if lat_txt or lng_txt:
                    coords = f"{lat_txt},{lng_txt}"

            cliente = models.Cliente(
                numero_cliente=safe_int(raw_num),
                nombre=(row.get("nombre") or "").strip(),
                direccion=row.get("direccion") or None,
                barrio=row.get("barrio") or None,
                telefono=row.get("telefono") or None,
                vendedor=row.get("vendedor") or None,
                descuento_porcentaje=to_descuento(raw_desc),
                comentario=row.get("comentario_adicional") or None,
                coordenadas=coords,
                # deuda del CSV ya viene como entero grande (ej 725400),
                # lo guardamos tal cual en centavos. Si después vemos que está desfasado,
                # ajustamos la escala.
                deuda_centavos=safe_int(raw_deuda) or 0,
                entrega_info=row.get("tipo_entrega") or None,
            )
            db.add(cliente)

        db.commit()
        print("Clientes importados OK")
    finally:
        db.close()


def importar_productos(csv_path: str = "productos_nortsur.csv"):
    """
    Asumimos columnas algo así:
    codigo, nombre, categoria, presentacion, precio
    (si cambian, ajustamos luego los nombres en row.get)
    """
    db = SessionLocal()
    try:
        for idx, row in enumerate(get_dict_reader(csv_path), start=1):
            raw_precio = (
                row.get("precio")
                or row.get("precio_lista")
                or row.get("PRECIO")
                or ""
            )

            prod = models.Producto(
                codigo=(row.get("codigo") or row.get("CODIGO") or "").strip(),
                nombre=(row.get("nombre") or row.get("NOMBRE") or "").strip(),
                categoria=row.get("categoria") or row.get("CATEGORIA") or None,
                presentacion=row.get("presentacion")
                or row.get("PRESENTACION")
                or None,
                precio_centavos=to_centavos(raw_precio),
            )
            db.add(prod)

        db.commit()
        print("Productos importados OK")
    finally:
        db.close()


if __name__ == "__main__":
    importar_clientes()
    importar_productos()
