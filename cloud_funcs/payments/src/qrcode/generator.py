import io
import json

import qrcode
from cryptography.fernet import Fernet
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from cloud_funcs.payments.src.schema.qr_data import QRData
from core.config import settings

# MacOS font paths
FONT_PATH_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_PATH_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_PATH_ITALIC = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"


async def create_partyup_ticket(
    qrdata: QRData,
) -> bytes:
    """Generate a vertically balanced PartyUp! ticket with dynamic font sizing for names."""

    # Function to auto-adjust font size
    def _fit_text(
        text: str,
        max_width: int,
        font_path: str,
        starting_size: int,
    ) -> ImageFont.FreeTypeFont:
        size: int = starting_size
        font: ImageFont.FreeTypeFont = ImageFont.truetype(
            font_path,
            size,
        )
        bbox: tuple[float, float, float, float] = draw.textbbox(
            (0, 0),
            text,
            font=font,
        )
        text_width: float = bbox[2] - bbox[0]
        while text_width > max_width and size > 10:
            size -= 1
            font = ImageFont.truetype(font_path, size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
        return font

    # QR Code
    json_bytes: bytes = json.dumps(
        qrdata.model_dump(), separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    fernet = Fernet(settings.FERNET_KEY)
    token_bytes: bytes = fernet.encrypt(json_bytes)
    token_str: str = token_bytes.decode("utf-8")
    print(token_str)
    qr_img: Image.Image = qrcode.make(token_str).resize((260, 260)).convert("RGB")  # type: ignore
    # 2Background
    width, height = 500, 720
    base: Image.Image = Image.new("RGB", (width, height), (11, 17, 32))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(base)
    # Neon gradient
    for i in range(height):
        color: tuple[int, int, int] = (11, 17, min(32 + int(i * 0.08), 60))
        draw.line([(0, i), (width, i)], fill=color)
    # Neon border glow
    glow: Image.Image = Image.new("RGB", (width, height), (0, 0, 0))
    glow_draw: ImageDraw.ImageDraw = ImageDraw.Draw(glow)
    glow_draw.rounded_rectangle(
        (10, 10, width - 10, height - 10), radius=30, fill=(0, 255, 255)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    base = Image.blend(glow, base, 0.9)
    draw = ImageDraw.Draw(base)
    # Fonts
    title_font: ImageFont.FreeTypeFont = ImageFont.truetype(FONT_PATH_BOLD, 48)
    label_font: ImageFont.FreeTypeFont = ImageFont.truetype(FONT_PATH_ITALIC, 28)
    small_font: ImageFont.FreeTypeFont = ImageFont.truetype(FONT_PATH_BOLD, 22)
    # Header
    draw.text(
        (width // 2 - 100, 20),
        "PartyUp!",
        fill="#00FFFF",
        font=title_font,
    )
    draw.line(
        [(50, 100), (width - 50, 100)],
        fill="#00FFFF",
        width=2,
    )
    # 5Vertical positions
    section_height = 60
    current_y = 120
    # Event info
    event_label = "Event:"
    event_name = qrdata.event.name if qrdata.event.name else "PartyUp! Event"
    # Center label
    bbox = draw.textbbox(
        (0, 0),
        event_label,
        font=label_font,
    )
    label_w: float = bbox[2] - bbox[0]
    draw.text(
        ((width - label_w) // 2, current_y),
        event_label,
        fill="#F19CF2",
        font=label_font,
    )
    # Fit and draw event name (centered)
    max_text_width = width - 100
    event_name_font: ImageFont.FreeTypeFont = _fit_text(
        event_name,
        max_text_width,
        FONT_PATH_BOLD,
        28,
    )
    bbox = draw.textbbox(
        (0, 0),
        event_name,
        font=event_name_font,
    )
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((width - text_w) // 2, current_y + 30),
        event_name,
        fill="white",
        font=event_name_font,
    )
    current_y += section_height + 30
    # Attendee info
    attendee_label = "Attendee:"
    attendee_name = (
        qrdata.attendee.name if qrdata.attendee.name else "PartyUp! Events Attendee"
    )
    # Center label
    bbox = draw.textbbox(
        (0, 0),
        attendee_label,
        font=label_font,
    )
    label_w = bbox[2] - bbox[0]
    draw.text(
        ((width - label_w) // 2, current_y),
        attendee_label,
        fill="#F19CF2",
        font=label_font,
    )

    # Fit and draw attendee name (centered)
    attendee_name_font: ImageFont.FreeTypeFont = _fit_text(
        attendee_name,
        max_text_width,
        FONT_PATH_BOLD,
        28,
    )
    bbox = draw.textbbox(
        (0, 0),
        attendee_name,
        font=attendee_name_font,
    )
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((width - text_w) // 2, current_y + 30),
        attendee_name,
        fill="white",
        font=attendee_name_font,
    )
    current_y += section_height + 20
    # Date (centered)
    date_text: str = f"Date: {qrdata.payment.timestamp}"
    bbox: tuple[float, float, float, float] = draw.textbbox(
        (0, 0),
        date_text,
        font=small_font,
    )
    date_w: float = bbox[2] - bbox[0]
    draw.text(
        ((width - date_w) // 2, current_y),
        date_text,
        fill="#F9E888",
        font=small_font,
    )
    current_y += 60
    # Verified badge (centered, outlined)
    badge_w, badge_h = 220, 50
    badge_x = (width - badge_w) // 2
    badge_y = current_y
    badge_color = "#00FFFF"  # same as previous filled color

    # Draw rectangle outline
    draw.rounded_rectangle(
        (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
        radius=12,
        outline=badge_color,
        width=3,  # thickness of the outline
        fill=None,  # no fill
    )

    # Draw text inside rectangle
    bbox = draw.textbbox((0, 0), "VERIFIED", font=small_font)
    text_w: float = bbox[2] - bbox[0]
    text_h: float = bbox[3] - bbox[1]
    draw.text(
        (badge_x + (badge_w - text_w) // 2, badge_y + (badge_h - text_h) // 2),
        "VERIFIED",
        fill=badge_color,  # same as rectangle
        font=small_font,
    )
    current_y += badge_h + 30
    # QR Code at bottom
    qr_position: tuple[int, int] = (width // 2 - 130, current_y)
    glow_layer: Image.Image = Image.new(
        "RGB",
        base.size,
        (0, 0, 0),
    )
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.ellipse(
        (
            qr_position[0] - 20,
            qr_position[1] - 20,
            qr_position[0] + 300,
            qr_position[1] + 300,
        ),
        fill=(0, 255, 255),
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(30))
    base = Image.blend(base, glow_layer, 0.3)
    base.paste(qr_img, qr_position)  # type: ignore

    import os

    output_path: str = f"{os.getcwd()}{qrdata.event.guid}_{qrdata.attendee.guid}.png"
    with open(output_path, "w") as f:
        base.save(output_path, format="PNG")
        f.close()

    # Convert to bytes
    buffer = io.BytesIO()
    base.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()
