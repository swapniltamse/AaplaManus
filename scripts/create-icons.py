"""Generate tray status icons and the main app icon for Tauri."""
from PIL import Image, ImageDraw
import os

os.makedirs("src-tauri/icons", exist_ok=True)

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
    img.save(f"src-tauri/icons/{filename}")
    print(f"Created src-tauri/icons/{filename}")

# 512x512 main app icon - dark navy background, blue circle
icon = Image.new("RGBA", (512, 512), (10, 17, 40, 255))
draw = ImageDraw.Draw(icon)
draw.ellipse([48, 48, 464, 464], fill=(59, 130, 246, 255))
icon.save("src-tauri/icons/icon.png")
print("Created src-tauri/icons/icon.png")
