"""
Genera los 5 fondos de tarjeta para la promo Día del Padre Pauletti.
Correr una sola vez: python generar_fondos.py
"""
from PIL import Image, ImageDraw
import math, os

W, H = 1200, 1800
OUT = "templates"
os.makedirs(OUT, exist_ok=True)


def gradiente_vertical(draw, color_top, color_bot, w=W, h=H):
    for y in range(h):
        t = y / h
        r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def borde_doble(draw, color, grosor_ext=18, grosor_int=6, margen=40):
    draw.rectangle([margen, margen, W-margen, H-margen],
                   outline=color, width=grosor_ext)
    m2 = margen + grosor_ext + 10
    draw.rectangle([m2, m2, W-m2, H-m2],
                   outline=color, width=grosor_int)


def esquinas_ornamentales(draw, color, margen=60, largo=80, grosor=6):
    puntos = [
        (margen, margen), (margen+largo, margen),
        (margen, margen+largo),
        (W-margen, margen), (W-margen-largo, margen),
        (W-margen, margen+largo),
        (margen, H-margen), (margen+largo, H-margen),
        (margen, H-margen-largo),
        (W-margen, H-margen), (W-margen-largo, H-margen),
        (W-margen, H-margen-largo),
    ]
    esquinas = [
        [(margen, margen+largo), (margen, margen), (margen+largo, margen)],
        [(W-margen-largo, margen), (W-margen, margen), (W-margen, margen+largo)],
        [(margen, H-margen-largo), (margen, H-margen), (margen+largo, H-margen)],
        [(W-margen-largo, H-margen), (W-margen, H-margen), (W-margen, H-margen-largo)],
    ]
    for pts in esquinas:
        draw.line(pts, fill=color, width=grosor)


def circulo_foto(draw, color_borde, alpha=60):
    cx, cy, r = 600, 380, 230
    for i in range(3, 0, -1):
        draw.ellipse([cx-r-i*8, cy-r-i*8, cx+r+i*8, cy+r+i*8],
                     outline=color_borde + (alpha,), width=4)


def linea_separadora(draw, color, y=620, margen=120):
    draw.line([(margen, y), (W-margen, y)], fill=color, width=3)
    draw.ellipse([W//2-6, y-6, W//2+6, y+6], fill=color)


# ── 1. CLÁSICO ────────────────────────────────────────────────────────────────
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img, "RGBA")
gradiente_vertical(d, (252, 248, 238), (240, 230, 210))
# Textura sutil: líneas diagonales muy suaves
for i in range(0, W+H, 30):
    d.line([(i, 0), (0, i)], fill=(200, 190, 170, 25), width=1)
borde_doble(d, (180, 155, 110))
esquinas_ornamentales(d, (160, 135, 90))
linea_separadora(d, (180, 155, 110))
d.ellipse([W//2-4, 618-4, W//2+4, 618+4], fill=(160, 135, 90))
circulo_foto(d, (180, 155, 110))
img.save(f"{OUT}/clasico.png")
print("clasico.png ✓")

# ── 2. ELEGANTE ───────────────────────────────────────────────────────────────
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img, "RGBA")
gradiente_vertical(d, (18, 18, 28), (8, 8, 18))
# Patrón de puntos dorados
for x in range(0, W, 60):
    for y in range(0, H, 60):
        d.ellipse([x-1, y-1, x+1, y+1], fill=(180, 150, 80, 40))
borde_doble(d, (200, 170, 90), grosor_ext=14, grosor_int=4)
esquinas_ornamentales(d, (210, 180, 100), largo=100, grosor=5)
linea_separadora(d, (200, 170, 90))
# Línea inferior ornamental
linea_separadora(d, (200, 170, 90), y=1300)
circulo_foto(d, (200, 170, 90), alpha=80)
img.save(f"{OUT}/elegante.png")
print("elegante.png ✓")

# ── 3. DIVERTIDO ──────────────────────────────────────────────────────────────
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img, "RGBA")
gradiente_vertical(d, (255, 220, 60), (255, 175, 30))
# Confeti geométrico
import random
random.seed(42)
shapes = [(255,100,50), (80,180,120), (60,130,220), (220,60,120), (255,255,255)]
for _ in range(120):
    x, y = random.randint(0, W), random.randint(0, H)
    sz = random.randint(12, 35)
    col = random.choice(shapes) + (120,)
    if random.random() > 0.5:
        d.rectangle([x, y, x+sz, y+sz], fill=col)
    else:
        d.ellipse([x, y, x+sz, y+sz], fill=col)
borde_doble(d, (200, 80, 30), grosor_ext=20, grosor_int=8)
esquinas_ornamentales(d, (200, 80, 30), largo=90, grosor=8)
linea_separadora(d, (200, 80, 30))
circulo_foto(d, (255, 255, 255))
img.save(f"{OUT}/divertido.png")
print("divertido.png ✓")

# ── 4. FUTBOLERO ──────────────────────────────────────────────────────────────
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img, "RGBA")
gradiente_vertical(d, (20, 100, 40), (10, 70, 25))
# Líneas de cancha
for x in range(0, W+1, W):
    d.line([(x, 0), (x, H)], fill=(255, 255, 255, 30), width=3)
d.line([(0, H//2), (W, H//2)], fill=(255, 255, 255, 30), width=3)
d.ellipse([W//2-150, H//2-150, W//2+150, H//2+150],
          outline=(255, 255, 255, 30), width=3)
# Banda roja en los bordes
for margen, ancho in [(0, 40), (W-40, W)]:
    d.rectangle([margen, 0, ancho, H], fill=(180, 20, 20, 180))
borde_doble(d, (255, 255, 255), grosor_ext=16, grosor_int=5)
esquinas_ornamentales(d, (255, 220, 0), largo=90, grosor=7)
linea_separadora(d, (255, 255, 255))
circulo_foto(d, (255, 255, 255))
img.save(f"{OUT}/futbolero.png")
print("futbolero.png ✓")

# ── 5. ABUELO ─────────────────────────────────────────────────────────────────
img = Image.new("RGB", (W, H))
d = ImageDraw.Draw(img, "RGBA")
gradiente_vertical(d, (245, 232, 210), (225, 208, 180))
# Textura papel viejo: ruido muy suave
for _ in range(8000):
    x, y = random.randint(0, W-1), random.randint(0, H-1)
    v = random.randint(150, 200)
    d.point((x, y), fill=(v, v-10, v-20, 30))
# Manchas de tono cálido
for _ in range(8):
    x, y = random.randint(100, W-100), random.randint(100, H-100)
    sz = random.randint(80, 200)
    d.ellipse([x, y, x+sz, y+sz], fill=(200, 175, 140, 15))
borde_doble(d, (140, 105, 65), grosor_ext=20, grosor_int=7)
esquinas_ornamentales(d, (120, 85, 45), largo=100, grosor=7)
linea_separadora(d, (140, 105, 65))
linea_separadora(d, (140, 105, 65), y=1310)
circulo_foto(d, (140, 105, 65))
img.save(f"{OUT}/abuelo.png")
print("abuelo.png ✓")

print("\nTodos los fondos generados en /templates/")
