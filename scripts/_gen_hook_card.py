"""Genera una card estilo post-social (Reddit_Gossipz look) para overlay de gancho.
Uso local: py scripts/_gen_hook_card.py "pregunta" "Canal" out.png [avatar.png]
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
# Logo generado para el rebrand de Mind Checkpoint (2048px). Se usa el original,
# no el thumbnail de YouTube: ese viene a 240px y se ve blando al escalar.
DEFAULT_AVATAR = ROOT / "assets" / "mindcheckpoint_rebrand" / "avatar.png"

W = 1040
PAD = 36
RADIUS = 40

def load_font(size, bold=False):
    names = ["seguisb.ttf", "segoeuib.ttf"] if bold else ["segoeui.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            continue
    return ImageFont.truetype("arial.ttf", size)

def emoji_font(size):
    try:
        return ImageFont.truetype("seguiemj.ttf", size)
    except Exception:
        return load_font(size)

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def paste_avatar(img, avatar_path, x, y, size):
    """Pega el logo del canal recortado en circulo. Si no se puede cargar,
    devuelve False para que el llamador dibuje el fallback."""
    try:
        av = Image.open(avatar_path).convert("RGBA").resize((size, size), Image.LANCZOS)
    except Exception:
        return False
    # mascara circular con antialias (se dibuja x4 y se reduce)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    img.paste(av, (x, y), mask)
    return True


def draw_verified(draw, x, y, r=13):
    """Check azul de verificado, como el del ejemplo de referencia."""
    draw.ellipse([x, y, x + r * 2, y + r * 2], fill=(29, 155, 240, 255))
    cx, cy = x + r, y + r
    draw.line([(cx - r * 0.45, cy), (cx - r * 0.1, cy + r * 0.38),
               (cx + r * 0.5, cy - r * 0.4)],
              fill=(255, 255, 255, 255), width=max(2, r // 5), joint="curve")


def make_card(question: str, channel: str, out_path: str, avatar_path=None,
              punch: str | None = None):
    """`punch` = gancho visual de 3-5 palabras, enorme, sobre la pregunta.

    Kallaway (revisado 30 jul 2026): el gancho visual pesa mucho mas que el
    hablado porque se lee mas rapido de lo que se oye. Una card de una frase
    entera se lee demasiado despacio para entrar en la ventana que decide el
    swipe; estas 3-5 palabras se absorben de un vistazo.
    """
    name_font = load_font(30, bold=True)
    q_font = load_font(40, bold=True)
    meta_font = load_font(26)
    emo_font = emoji_font(34)
    punch_font = load_font(70, bold=True)

    tmp = Image.new("RGB", (10, 10))
    draw_probe = ImageDraw.Draw(tmp)

    text_w = W - PAD * 2 - 40
    lines = wrap_text(draw_probe, question, q_font, text_w)

    punch = (punch or "").strip()
    punch_lines = wrap_text(draw_probe, punch.upper(), punch_font, text_w) if punch else []
    punch_line_h = 80
    punch_h = (punch_line_h * len(punch_lines) + 24) if punch_lines else 0

    header_h = 90
    emoji_row_h = 50
    line_h = 50
    q_h = line_h * len(lines) + 20
    footer_h = 60
    H = header_h + emoji_row_h + punch_h + q_h + footer_h + PAD * 2

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, W, H], radius=RADIUS, fill=(18, 18, 22, 255))

    # avatar: logo real del canal recortado en circulo; si falta el archivo,
    # cae a un circulo liso con la inicial (nunca revienta la generacion)
    ax, ay, ad = PAD, PAD, 64
    av_path = avatar_path or DEFAULT_AVATAR
    if not paste_avatar(img, av_path, ax, ay, ad):
        draw.ellipse([ax, ay, ax + ad, ay + ad], fill=(60, 70, 230, 255))
        initial = (channel.lstrip("@") or "?")[0].upper()
        draw.text((ax + ad // 2, ay + ad // 2), initial, font=load_font(34, bold=True),
                  fill=(255, 255, 255, 255), anchor="mm")

    name_x = ax + ad + 20
    draw.text((name_x, ay + 8), channel, font=name_font, fill=(255, 255, 255, 255))
    name_w = draw.textlength(channel, font=name_font)
    draw_verified(draw, int(name_x + name_w + 12), ay + 12)

    y = header_h + PAD // 2
    emojis = "🐼 🐧 🌵 🐢 🍄 🐙 🍁"
    draw.text((PAD, y), emojis, font=emo_font, fill=(255, 255, 255, 255))

    y += emoji_row_h + 6

    # gancho visual: va ARRIBA de la pregunta y en amarillo, para que sea lo
    # primero que el ojo agarra antes de leer nada mas
    for line in punch_lines:
        draw.text((PAD, y), line, font=punch_font, fill=(255, 214, 0, 255))
        y += punch_line_h
    if punch_lines:
        y += 24

    for line in lines:
        draw.text((PAD, y), line, font=q_font, fill=(255, 255, 255, 255))
        y += line_h

    fy = H - footer_h - PAD // 2
    icon_font = emoji_font(28)
    draw.text((PAD, fy), "❤️", font=icon_font, fill=(220, 220, 220, 255))
    draw.text((PAD + 40, fy + 2), "99+", font=meta_font, fill=(220, 220, 220, 255))
    draw.text((PAD + 150, fy), "💬", font=icon_font, fill=(220, 220, 220, 255))
    draw.text((PAD + 195, fy + 2), "99+", font=meta_font, fill=(220, 220, 220, 255))
    draw.text((W - PAD - 150, fy), "↪️", font=icon_font, fill=(220, 220, 220, 255))
    draw.text((W - PAD - 105, fy + 2), "share", font=meta_font, fill=(220, 220, 220, 255))

    img.save(out_path)
    print("saved", out_path, img.size)

if __name__ == "__main__":
    question = sys.argv[1]
    channel = sys.argv[2]
    out = sys.argv[3]
    avatar = sys.argv[4] if len(sys.argv) > 4 else None
    punch = sys.argv[5] if len(sys.argv) > 5 else None
    make_card(question, channel, out, avatar, punch)
