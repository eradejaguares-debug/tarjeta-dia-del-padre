"""
generar_tarjetas.py
====================
Genera automáticamente la imagen final de cada tarjeta "Dedicatoria para Papá"
a partir del CSV exportado desde la planilla de Google Sheets conectada al
formulario de Jotform.

FLUJO DE USO:
1. Diseñá en Canva un fondo (template) por cada estilo: Clásico, Elegante,
   Divertido, Futbolero, Abuelo. Exportalos como PNG y guardalos en la
   carpeta ./templates con estos nombres exactos:
       templates/clasico.png
       templates/elegante.png
       templates/divertido.png
       templates/futbolero.png
       templates/abuelo.png
   (si falta alguno, el script usa un fondo simple de relleno para no romperse)

2. Exportá/descargá la planilla de Google Sheets como CSV (Archivo > Descargar
   > Valores separados por comas) y guardala como respuestas.csv.

3. Corré el script:
       python generar_tarjetas.py --csv respuestas.csv

4. Las imágenes finales quedan en ./tarjetas_generadas, una por pedido,
   nombradas tarjeta_pedido_<numero>.png. Mirá cada una antes de mandarla
   por WhatsApp para que el cliente la apruebe, y antes de imprimir cruzá
   el número de pedido contra la lista de pagos confirmados.

REQUISITOS (instalar una sola vez):
    pip install pillow requests
"""

import argparse
import csv
import os
import sys
import textwrap
import urllib.request
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps

# ---------------------------------------------------------------------------
# CONFIGURACIÓN: ajustá estos valores si tu diseño de Canva tiene otra
# distribución. Las coordenadas son (x, y) en píxeles, asumiendo templates
# de 1200x1800 (relación tarjeta vertical, buena para imprimir).
# ---------------------------------------------------------------------------

CANVAS_SIZE = (1200, 1800)

# Caja de texto donde va la frase (x0, y0, x1, y1)
TEXT_BOX = (120, 650, 1080, 1150)
TEXT_COLOR = (30, 30, 30)
FONT_PATH = "fonts/Lora-Regular.ttf"   # fuente de la frase. Reemplazá el archivo si querés otra.
FONT_SIZE_MAX = 64
FONT_SIZE_MIN = 28

# Línea de firma (nombres de hijos/familiares), debajo de la frase
SIGNATURE_BOX = (120, 1180, 1080, 1260)
SIGNATURE_FONT_PATH = "fonts/NothingYouCouldDo-Regular.ttf"  # estilo manuscrito para la firma
SIGNATURE_FONT_SIZE = 48

# Círculo donde va la foto, si el cliente subió una
PHOTO_CENTER = (600, 380)
PHOTO_RADIUS = 220

# Colores de fondo de respaldo si falta el template de un estilo
FALLBACK_BG_COLOR = {
    "Clásico": (245, 240, 230),
    "Elegante": (20, 20, 25),
    "Divertido": (255, 214, 102),
    "Futbolero": (180, 30, 30),
    "Abuelo": (235, 225, 205),
}

# Mapeo de las columnas del CSV exportado por Jotform/Google Sheets.
# Si tus columnas tienen otro texto exacto, ajustalo acá.
COLUMN_MAP = {
    "nombre": "Nombre",
    "whatsapp": "WhatsApp",
    "pedido": "Número de pedido",
    "confirmacion": "Confirmo que ya reservé mi pedido por WhatsApp y que supera los $22.000.",
    "frase_elegida": "Elegí la frase que más se parece a tu papá",
    "frase_propia": "Escribí tu frase para la tarjeta",
    "personalizacion": "Si tu frase tiene un dato para completar (club, años juntos, una palabra que lo describa), escribilo acá. Si no aplica, dejalo en blanco.",
    "hijos": "Nombres de hijos o familiares a incluir",
    "foto_url": "Subí una foto si querés que acompañe la tarjeta.",
    "estilo": "¿Qué estilo de tarjeta querés para tu papá?",
}

OPCION_FRASE_PROPIA = "Ninguna me cierra del todo, quiero escribir la mía"

# Palabras/placeholders dentro de las frases que se pueden reemplazar por el
# dato libre que el cliente puso en el campo de personalización.
PLACEHOLDERS = [
    "tu club",
    "mi club",
    "tu encanto (o tu terquedad)",
    "así de bueno",
]


def cargar_fuente(tamano, ruta=FONT_PATH):
    try:
        return ImageFont.truetype(ruta, tamano)
    except Exception:
        # Si no encuentra la fuente personalizada, usa una por defecto.
        return ImageFont.load_default()


def ajustar_texto_a_caja(draw, texto, caja, tamano_max, tamano_min):
    """Devuelve (fuente, lineas) que entran dentro de la caja, probando
    tamaños de fuente de mayor a menor."""
    ancho_caja = caja[2] - caja[0]
    alto_caja = caja[3] - caja[1]

    for tamano in range(tamano_max, tamano_min - 1, -2):
        fuente = cargar_fuente(tamano)
        # Estimamos cuántos caracteres entran por línea según el ancho promedio.
        ancho_promedio_char = max(fuente.getlength("a"), 1)
        chars_por_linea = max(int(ancho_caja / ancho_promedio_char), 5)
        lineas = textwrap.wrap(texto, width=chars_por_linea)

        alto_total = len(lineas) * (tamano + 10)
        if alto_total <= alto_caja:
            return fuente, lineas

    # Si ni con el tamaño mínimo entra, devolvemos igual el mínimo (se recorta)
    fuente = cargar_fuente(tamano_min)
    chars_por_linea = max(int(ancho_caja / max(fuente.getlength("a"), 1)), 5)
    lineas = textwrap.wrap(texto, width=chars_por_linea)
    return fuente, lineas


def dibujar_texto_centrado(draw, lineas, fuente, caja, color):
    ancho_caja = caja[2] - caja[0]
    alto_linea = fuente.size + 10
    alto_total = len(lineas) * alto_linea
    y = caja[1] + (caja[3] - caja[1] - alto_total) // 2

    for linea in lineas:
        ancho_linea = fuente.getlength(linea)
        x = caja[0] + (ancho_caja - ancho_linea) // 2
        draw.text((x, y), linea, font=fuente, fill=color)
        y += alto_linea


def pegar_foto_circular(imagen_base, foto_url):
    try:
        with urllib.request.urlopen(foto_url, timeout=10) as resp:
            datos = resp.read()
        foto = Image.open(BytesIO(datos)).convert("RGB")
    except Exception as e:
        print(f"  [aviso] no se pudo descargar la foto ({foto_url}): {e}")
        return imagen_base

    diametro = PHOTO_RADIUS * 2
    foto = ImageOps.fit(foto, (diametro, diametro), centering=(0.5, 0.4))

    mascara = Image.new("L", (diametro, diametro), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, diametro, diametro), fill=255)

    foto_circular = Image.new("RGBA", (diametro, diametro))
    foto_circular.paste(foto, (0, 0), mascara)

    pos = (PHOTO_CENTER[0] - PHOTO_RADIUS, PHOTO_CENTER[1] - PHOTO_RADIUS)
    imagen_base.paste(foto_circular, pos, foto_circular)
    return imagen_base


def cargar_fondo(estilo, templates_dir):
    nombre_archivo = {
        "Clásico": "clasico.png",
        "Elegante": "elegante.png",
        "Divertido": "divertido.png",
        "Futbolero": "futbolero.png",
        "Abuelo": "abuelo.png",
    }.get(estilo, "clasico.png")

    ruta = os.path.join(templates_dir, nombre_archivo)
    if os.path.exists(ruta):
        return Image.open(ruta).convert("RGB").resize(CANVAS_SIZE)

    print(f"  [aviso] no se encontró {ruta}, uso un fondo simple de respaldo.")
    color = FALLBACK_BG_COLOR.get(estilo, (230, 230, 230))
    return Image.new("RGB", CANVAS_SIZE, color)


def armar_frase_final(fila):
    frase = fila.get(COLUMN_MAP["frase_elegida"], "").strip()
    if frase == OPCION_FRASE_PROPIA or not frase:
        frase = fila.get(COLUMN_MAP["frase_propia"], "").strip()

    dato = fila.get(COLUMN_MAP["personalizacion"], "").strip()
    if dato:
        for placeholder in PLACEHOLDERS:
            if placeholder in frase:
                frase = frase.replace(placeholder, dato)
                break

    return frase


def generar_tarjeta(fila, templates_dir, output_dir):
    pedido = fila.get(COLUMN_MAP["pedido"], "SIN_NUMERO").strip() or "SIN_NUMERO"
    estilo = fila.get(COLUMN_MAP["estilo"], "Clásico").strip() or "Clásico"
    frase = armar_frase_final(fila)
    hijos = fila.get(COLUMN_MAP["hijos"], "").strip()
    foto_url = fila.get(COLUMN_MAP["foto_url"], "").strip()

    print(f"Generando tarjeta del pedido {pedido} (estilo: {estilo})...")

    imagen = cargar_fondo(estilo, templates_dir).convert("RGBA")
    draw = ImageDraw.Draw(imagen)

    if foto_url:
        imagen = pegar_foto_circular(imagen, foto_url)
        draw = ImageDraw.Draw(imagen)

    fuente, lineas = ajustar_texto_a_caja(draw, frase, TEXT_BOX, FONT_SIZE_MAX, FONT_SIZE_MIN)
    dibujar_texto_centrado(draw, lineas, fuente, TEXT_BOX, TEXT_COLOR)

    if hijos:
        firma = f"Con cariño, {hijos}"
        fuente_firma = cargar_fuente(SIGNATURE_FONT_SIZE, ruta=SIGNATURE_FONT_PATH)
        dibujar_texto_centrado(draw, [firma], fuente_firma, SIGNATURE_BOX, TEXT_COLOR)

    os.makedirs(output_dir, exist_ok=True)
    ruta_salida = os.path.join(output_dir, f"tarjeta_pedido_{pedido}.png")
    imagen.convert("RGB").save(ruta_salida, quality=95)
    print(f"  -> guardada en {ruta_salida}")
    return ruta_salida


def main():
    parser = argparse.ArgumentParser(description="Genera las tarjetas personalizadas Día del Padre Pauletti.")
    parser.add_argument("--csv", required=True, help="Ruta al CSV exportado de Google Sheets / Jotform.")
    parser.add_argument("--templates_dir", default="templates", help="Carpeta con los fondos por estilo.")
    parser.add_argument("--output_dir", default="tarjetas_generadas", help="Carpeta de salida de las imágenes.")
    parser.add_argument("--limit", type=int, default=None, help="Generar solo las primeras N filas (para probar).")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"No encuentro el archivo {args.csv}")
        sys.exit(1)

    with open(args.csv, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    if args.limit:
        filas = filas[: args.limit]

    print(f"Encontradas {len(filas)} respuestas en el CSV. Generando tarjetas...\n")

    rutas = []
    for fila in filas:
        confirmacion = fila.get(COLUMN_MAP["confirmacion"], "")
        rutas.append(generar_tarjeta(fila, args.templates_dir, args.output_dir))
        if "después confirmo" in confirmacion.lower():
            print("  [nota] esta persona aún no confirmó el pago, revisar antes de imprimir.\n")
        else:
            print()

    print(f"Listo. {len(rutas)} tarjetas generadas en '{args.output_dir}'.")
    print("Revisá cada imagen antes de mandarla por WhatsApp para aprobación,")
    print("y cruzá el número de pedido contra la lista de pagos confirmados antes de imprimir.")


if __name__ == "__main__":
    main()
