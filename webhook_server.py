"""
webhook_server.py
==================
Servidor que recibe el webhook de Jotform apenas alguien aprieta "GENERAR TARJETA",
genera la imagen de la tarjeta automáticamente, y la deja lista para ver y aprobar.

CÓMO FUNCIONA
1. Jotform manda un webhook a este servidor con el submissionID apenas se envía el formulario.
2. Este servidor le pide a la API de Jotform los datos completos de esa respuesta
   (usando tu API Key de Jotform).
3. Genera la tarjeta con la misma lógica que generar_tarjetas.py.
4. La deja disponible en /tarjeta/<submissionID> para verla y aprobarla desde el celular.

CONFIGURACIÓN NECESARIA (variables de entorno):
    JOTFORM_API_KEY   -> la sacás en Jotform: arriba a la derecha, tu foto de perfil >
                         Configuración de cuenta > API. Generás una clave nueva ahí.
    PORT              -> opcional, puerto donde corre el servidor (default 5000)

INSTALAR:
    pip install flask pillow requests

PROBAR RÁPIDO EN LOCAL (sin pagar hosting, con ngrok):
    1. export JOTFORM_API_KEY=tu_clave_acá
    2. python webhook_server.py
    3. en otra terminal: ngrok http 5000
    4. copiá la URL https que te da ngrok (algo como https://abcd1234.ngrok.app)

CONFIGURAR EN JOTFORM:
    1. Form Builder > Settings > Integrations > buscar "Webhooks" > agregar:
           https://TU-URL-DE-NGROK-O-DEPLOY/webhook
    2. Form Builder > Settings > Thank You Page > elegir "Redirect to URL" y poner:
           https://TU-URL-DE-NGROK-O-DEPLOY/tarjeta/{submissionID}
       (Jotform reemplaza {submissionID} automáticamente por el número real)

IMPORTANTE: si corrés esto con ngrok gratis, la URL cambia cada vez que lo reiniciás,
así que tendrías que volver a pegarla en Jotform. Para dejarlo fijo durante toda la
promo, lo ideal es desplegarlo en un servicio como Render o Railway (plan gratuito).
"""

import os
import json
import random
import textwrap
from io import BytesIO

import requests
from flask import Flask, request, render_template_string, abort, send_file
from PIL import Image, ImageDraw, ImageFont, ImageOps

app = Flask(__name__)

JOTFORM_API_KEY = os.environ.get("JOTFORM_API_KEY", "")
DATA_FILE = "submissions.json"
OUTPUT_DIR = "tarjetas_generadas"
TEMPLATES_DIR = "templates"


# ---------------------------------------------------------------------
# Generación de fondos (se ejecuta al arrancar si no existen los PNG)
# ---------------------------------------------------------------------

def _gradiente(draw, top, bot, w=1200, h=1800):
    for y in range(h):
        t = y / h
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _borde(draw, color, ge=18, gi=6, m=40):
    draw.rectangle([m, m, 1200-m, 1800-m], outline=color, width=ge)
    m2 = m + ge + 10
    draw.rectangle([m2, m2, 1200-m2, 1800-m2], outline=color, width=gi)


def _esquinas(draw, color, m=60, largo=80, g=6):
    for pts in [
        [(m, m+largo), (m, m), (m+largo, m)],
        [(1200-m-largo, m), (1200-m, m), (1200-m, m+largo)],
        [(m, 1800-m-largo), (m, 1800-m), (m+largo, 1800-m)],
        [(1200-m-largo, 1800-m), (1200-m, 1800-m), (1200-m, 1800-m-largo)],
    ]:
        draw.line(pts, fill=color, width=g)


def _sep(draw, color, y=620, m=120):
    draw.line([(m, y), (1200-m, y)], fill=color, width=3)
    draw.ellipse([600-6, y-6, 600+6, y+6], fill=color)


def _circulo(draw, color, alpha=70):
    cx, cy, r = 600, 380, 230
    for i in range(3, 0, -1):
        draw.ellipse([cx-r-i*8, cy-r-i*8, cx+r+i*8, cy+r+i*8],
                     outline=color + (alpha,), width=4)


def generar_fondos_si_faltan():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    W, H = 1200, 1800

    # Clásico
    p = os.path.join(TEMPLATES_DIR, "clasico.png")
    if not os.path.exists(p):
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img, "RGBA")
        _gradiente(d, (252, 248, 238), (240, 230, 210))
        for i in range(0, W+H, 30):
            d.line([(i, 0), (0, i)], fill=(200, 190, 170, 18), width=1)
        _borde(d, (180, 155, 110))
        _esquinas(d, (160, 135, 90))
        _sep(d, (180, 155, 110))
        _circulo(d, (180, 155, 110))
        img.save(p)

    # Elegante
    p = os.path.join(TEMPLATES_DIR, "elegante.png")
    if not os.path.exists(p):
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img, "RGBA")
        _gradiente(d, (18, 18, 28), (8, 8, 18))
        for x in range(0, W, 60):
            for y in range(0, H, 60):
                d.ellipse([x-1, y-1, x+1, y+1], fill=(180, 150, 80, 35))
        _borde(d, (200, 170, 90), ge=14, gi=4)
        _esquinas(d, (210, 180, 100), largo=100, g=5)
        _sep(d, (200, 170, 90))
        _sep(d, (200, 170, 90), y=1300)
        _circulo(d, (200, 170, 90), alpha=90)
        img.save(p)

    # Divertido
    p = os.path.join(TEMPLATES_DIR, "divertido.png")
    if not os.path.exists(p):
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img, "RGBA")
        _gradiente(d, (255, 220, 60), (255, 175, 30))
        rng = random.Random(42)
        colores = [(255,100,50), (80,180,120), (60,130,220), (220,60,120), (255,255,255)]
        for _ in range(120):
            x, y = rng.randint(0, W), rng.randint(0, H)
            sz = rng.randint(12, 35)
            col = rng.choice(colores) + (110,)
            if rng.random() > 0.5:
                d.rectangle([x, y, x+sz, y+sz], fill=col)
            else:
                d.ellipse([x, y, x+sz, y+sz], fill=col)
        _borde(d, (200, 80, 30), ge=20, gi=8)
        _esquinas(d, (200, 80, 30), largo=90, g=8)
        _sep(d, (200, 80, 30))
        _circulo(d, (255, 255, 255))
        img.save(p)

    # Futbolero
    p = os.path.join(TEMPLATES_DIR, "futbolero.png")
    if not os.path.exists(p):
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img, "RGBA")
        _gradiente(d, (20, 100, 40), (10, 70, 25))
        d.line([(0, H//2), (W, H//2)], fill=(255, 255, 255, 25), width=3)
        d.ellipse([W//2-150, H//2-150, W//2+150, H//2+150],
                  outline=(255, 255, 255, 25), width=3)
        d.rectangle([0, 0, 45, H], fill=(180, 20, 20, 190))
        d.rectangle([W-45, 0, W, H], fill=(180, 20, 20, 190))
        _borde(d, (255, 255, 255), ge=16, gi=5)
        _esquinas(d, (255, 220, 0), largo=90, g=7)
        _sep(d, (255, 255, 255))
        _circulo(d, (255, 255, 255))
        img.save(p)

    # Abuelo
    p = os.path.join(TEMPLATES_DIR, "abuelo.png")
    if not os.path.exists(p):
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img, "RGBA")
        _gradiente(d, (245, 232, 210), (225, 208, 180))
        rng = random.Random(7)
        for _ in range(6000):
            x, y = rng.randint(0, W-1), rng.randint(0, H-1)
            v = rng.randint(155, 195)
            d.point((x, y), fill=(v, v-10, v-20, 28))
        for _ in range(8):
            x, y = rng.randint(100, W-100), rng.randint(100, H-100)
            sz = rng.randint(80, 200)
            d.ellipse([x, y, x+sz, y+sz], fill=(200, 175, 140, 15))
        _borde(d, (140, 105, 65), ge=20, gi=7)
        _esquinas(d, (120, 85, 45), largo=100, g=7)
        _sep(d, (140, 105, 65))
        _sep(d, (140, 105, 65), y=1310)
        _circulo(d, (140, 105, 65))
        img.save(p)


generar_fondos_si_faltan()

# ---- Mismo bloque de configuración visual que generar_tarjetas.py ----
CANVAS_SIZE = (1200, 1800)
TEXT_BOX = (120, 650, 1080, 1150)
TEXT_COLOR = (30, 30, 30)
FONT_PATH = "Fonts/Lora-Regular.ttf"
FONT_SIZE_MAX = 64
FONT_SIZE_MIN = 28
SIGNATURE_BOX = (120, 1180, 1080, 1260)
SIGNATURE_FONT_PATH = "Fonts/NothingYouCouldDo-Regular.ttf"
SIGNATURE_FONT_SIZE = 48
PHOTO_CENTER = (600, 380)
PHOTO_RADIUS = 220
FALLBACK_BG_COLOR = {
    "Clásico": (245, 240, 230),
    "Elegante": (20, 20, 25),
    "Divertido": (255, 214, 102),
    "Futbolero": (180, 30, 30),
    "Abuelo": (235, 225, 205),
}

# Etiquetas EXACTAS de las preguntas tal como están escritas en el formulario.
# Si en algún momento editás el texto de una pregunta en Jotform, actualizá acá también.
LABELS = {
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
PLACEHOLDERS = ["tu club", "mi club", "tu encanto (o tu terquedad)", "así de bueno"]


# ---------------------------------------------------------------------
# Generación de imagen (idéntica en lógica a generar_tarjetas.py)
# ---------------------------------------------------------------------

def cargar_fuente(tamano, ruta=FONT_PATH):
    try:
        return ImageFont.truetype(ruta, tamano)
    except Exception:
        return ImageFont.load_default()


def ajustar_texto_a_caja(texto, caja, tamano_max, tamano_min):
    ancho_caja = caja[2] - caja[0]
    alto_caja = caja[3] - caja[1]
    for tamano in range(tamano_max, tamano_min - 1, -2):
        fuente = cargar_fuente(tamano)
        ancho_promedio_char = max(fuente.getlength("a"), 1)
        chars_por_linea = max(int(ancho_caja / ancho_promedio_char), 5)
        lineas = textwrap.wrap(texto, width=chars_por_linea)
        alto_total = len(lineas) * (tamano + 10)
        if alto_total <= alto_caja:
            return fuente, lineas
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
        resp = requests.get(foto_url, timeout=10)
        resp.raise_for_status()
        datos_foto = resp.content
        foto = Image.open(BytesIO(datos_foto)).convert("RGB")
    except Exception as e:
        print(f"  [aviso] no se pudo descargar la foto: {e}")
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


def cargar_fondo(estilo):
    nombre_archivo = {
        "Clásico": "clasico.png", "Elegante": "elegante.png",
        "Divertido": "divertido.png", "Futbolero": "futbolero.png",
        "Abuelo": "abuelo.png",
    }.get(estilo, "clasico.png")
    ruta = os.path.join(TEMPLATES_DIR, nombre_archivo)
    if os.path.exists(ruta):
        return Image.open(ruta).convert("RGB").resize(CANVAS_SIZE)
    color = FALLBACK_BG_COLOR.get(estilo, (230, 230, 230))
    return Image.new("RGB", CANVAS_SIZE, color)


def armar_frase_final(datos):
    frase = (datos.get("frase_elegida") or "").strip()
    if frase == OPCION_FRASE_PROPIA or not frase:
        frase = (datos.get("frase_propia") or "").strip()
    dato = (datos.get("personalizacion") or "").strip()
    if dato:
        for placeholder in PLACEHOLDERS:
            if placeholder in frase:
                frase = frase.replace(placeholder, dato)
                break
    return frase


def generar_imagen(datos, submission_id):
    estilo = (datos.get("estilo") or "Clásico").strip() or "Clásico"
    frase = armar_frase_final(datos)
    hijos = (datos.get("hijos") or "").strip()
    foto_url = (datos.get("foto_url") or "").strip()

    imagen = cargar_fondo(estilo).convert("RGBA")
    if foto_url:
        imagen = pegar_foto_circular(imagen, foto_url)
    draw = ImageDraw.Draw(imagen)

    fuente, lineas = ajustar_texto_a_caja(frase, TEXT_BOX, FONT_SIZE_MAX, FONT_SIZE_MIN)
    dibujar_texto_centrado(draw, lineas, fuente, TEXT_BOX, TEXT_COLOR)

    if hijos:
        firma = f"Con cariño, {hijos}"
        fuente_firma = cargar_fuente(SIGNATURE_FONT_SIZE, ruta=SIGNATURE_FONT_PATH)
        dibujar_texto_centrado(draw, [firma], fuente_firma, SIGNATURE_BOX, TEXT_COLOR)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ruta_salida = os.path.abspath(os.path.join(OUTPUT_DIR, f"tarjeta_{submission_id}.png"))
    imagen.convert("RGB").save(ruta_salida, quality=95)
    return ruta_salida


# ---------------------------------------------------------------------
# Base de datos mínima (un archivo JSON, alcanza para esta campaña puntual)
# ---------------------------------------------------------------------

def leer_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_db(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------
# Traer la respuesta completa desde la API de Jotform por su submissionID
# ---------------------------------------------------------------------

def obtener_datos_de_submission(submission_id):
    url = f"https://api.jotform.com/submission/{submission_id}"
    resp = requests.get(url, params={"apiKey": JOTFORM_API_KEY}, timeout=15)
    resp.raise_for_status()
    contenido = resp.json()["content"]
    answers = contenido.get("answers", {})

    por_etiqueta = {}
    for item in answers.values():
        etiqueta = (item.get("text") or "").strip()
        valor = item.get("answer", "")
        if isinstance(valor, dict):
            valor = valor.get("url", "") or json.dumps(valor)
        if isinstance(valor, list):
            valor = valor[0] if valor else ""
        por_etiqueta[etiqueta] = valor

    datos = {}
    for clave, etiqueta in LABELS.items():
        datos[clave] = por_etiqueta.get(etiqueta, "")
    return datos


# ---------------------------------------------------------------------
# Rutas del servidor
# ---------------------------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    submission_id = request.form.get("submissionID")
    if not submission_id and request.is_json:
        submission_id = (request.json or {}).get("submissionID")

    if not submission_id:
        print("Webhook sin submissionID. Payload crudo:", request.form, request.get_data())
        return "sin submissionID", 400

    print(f"Nueva respuesta recibida: {submission_id}")
    try:
        datos = obtener_datos_de_submission(submission_id)
        ruta_imagen = generar_imagen(datos, submission_id)
    except Exception as e:
        print(f"Error generando la tarjeta de {submission_id}: {e}")
        return "error generando la tarjeta", 500

    db = leer_db()
    db[submission_id] = {
        "nombre": datos.get("nombre", ""),
        "whatsapp": datos.get("whatsapp", ""),
        "pedido": datos.get("pedido", ""),
        "confirmacion": datos.get("confirmacion", ""),
        "imagen": ruta_imagen,
        "aprobada": False,
    }
    guardar_db(db)
    print(f"Tarjeta generada: {ruta_imagen}")
    return "ok", 200


PAGINA_TARJETA = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Tu tarjeta para Papá</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: sans-serif; text-align: center; background:#faf7f2; padding: 20px; }
  img { max-width: 360px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.2); }
  button { font-size: 18px; padding: 12px 28px; margin-top: 20px; border-radius: 8px; border: none; background:#1a7a3c; color: white; cursor:pointer; }
</style></head>
<body>
  <h2>Así quedó tu tarjeta</h2>
  <img src="/imagen/{{ submission_id }}" alt="Tarjeta para papá">
  <br>
  {% if aprobada %}
    <p>Gracias, ya quedó confirmada.</p>
  {% else %}
    <form method="post" action="/tarjeta/{{ submission_id }}/aprobar">
      <button type="submit">Confirmar esta tarjeta</button>
    </form>
  {% endif %}
</body></html>
"""


@app.route("/tarjeta/<submission_id>")
def ver_tarjeta(submission_id):
    db = leer_db()
    registro = db.get(submission_id)

    # Si no está en la DB o la imagen se perdió (filesystem efímero de Render),
    # la regeneramos on-demand desde la API de Jotform.
    if not registro or not os.path.exists(registro.get("imagen", "")):
        try:
            datos = obtener_datos_de_submission(submission_id)
            ruta_imagen = generar_imagen(datos, submission_id)
        except Exception as e:
            print(f"Error regenerando tarjeta {submission_id}: {e}")
            abort(404)
        aprobada = registro.get("aprobada", False) if registro else False
        db[submission_id] = {
            "nombre": datos.get("nombre", ""),
            "whatsapp": datos.get("whatsapp", ""),
            "pedido": datos.get("pedido", ""),
            "confirmacion": datos.get("confirmacion", ""),
            "imagen": ruta_imagen,
            "aprobada": aprobada,
        }
        guardar_db(db)
        registro = db[submission_id]

    return render_template_string(PAGINA_TARJETA, submission_id=submission_id, aprobada=registro["aprobada"])


@app.route("/imagen/<submission_id>")
def imagen(submission_id):
    db = leer_db()
    registro = db.get(submission_id)
    if not registro or not os.path.exists(registro["imagen"]):
        abort(404)
    return send_file(registro["imagen"], mimetype="image/png")


@app.route("/tarjeta/<submission_id>/aprobar", methods=["POST"])
def aprobar(submission_id):
    db = leer_db()
    if submission_id not in db:
        abort(404)
    db[submission_id]["aprobada"] = True
    guardar_db(db)
    return ver_tarjeta(submission_id)


if __name__ == "__main__":
    if not JOTFORM_API_KEY:
        print("[aviso] falta configurar la variable de entorno JOTFORM_API_KEY")
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
