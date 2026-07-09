"""Generate tray status icons and the main app icon for Tauri."""
import os
import pathlib
from PIL import Image, ImageDraw

REPO_ROOT = pathlib.Path(__file__).parent.parent
ICONS_DIR = REPO_ROOT / "src-tauri" / "icons"
os.makedirs(ICONS_DIR, exist_ok=True)

# 32x32 colored circles for tray status
tray_icons = [
    ("tray-amber.png", (245, 158, 11)),
    ("tray-green.png", (16, 185, 129)),
    ("tray-red.png",   (239, 68, 68)),
]
for filename, color in tray_icons:
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 28, 28], fill=color + (255,))
    img.save(ICONS_DIR / filename)
    print(f"Created {ICONS_DIR / filename}")

# 512x512 main app icon — dark navy background, blue circle
icon = Image.new("RGBA", (512, 512), (10, 17, 40, 255))
draw = ImageDraw.Draw(icon)
draw.ellipse([48, 48, 464, 464], fill=(59, 130, 246, 255))
icon.save(ICONS_DIR / "icon.png")
print(f"Created {ICONS_DIR / 'icon.png'}")

# ICO file — required by Tauri NSIS bundler (tauri.conf.json: "icons/icon.ico")
icon_ico = icon.resize((256, 256), Image.LANCZOS)
icon_ico.save(
    ICONS_DIR / "icon.ico",
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
)
print(f"Created {ICONS_DIR / 'icon.ico'}")
