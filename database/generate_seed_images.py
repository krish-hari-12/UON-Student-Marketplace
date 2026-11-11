# Generate placeholder images for demo marketplace listings.

import os
from PIL import Image, ImageDraw

COLORS = {
    "Textbooks": ("#2a7fb8", "#14385f"),
    "Goods": ("#009a44", "#0b5c31"),
    "Transport": ("#e8890c", "#8a4d00"),
    "Services": ("#7a3fa0", "#3d1e54"),
    "Electronics": ("#00696d", "#00383b"),
    "Housing": ("#c0392b", "#6e1f16"),
}

IMAGES = [
    ("seed_stat1070.png", "STAT1070", "Textbook"),
    ("seed_desk.png", "Study desk", "Goods"),
    ("seed_laptop.png", "HP laptop", "Electronics"),
    ("seed_bike.png", "Mountain bike", "Transport"),
    ("seed_fridge.png", "Mini fridge", "Goods"),
    ("seed_calculator.png", "Calculator", "Electronics"),
    ("seed_tutoring.png", "Tutoring", "Services"),
    ("seed_bedside.png", "Bedside table", "Housing"),
    ("seed_notes.png", "COMP6900 notes", "Textbook"),
    ("seed_scooter.png", "E-scooter", "Transport"),
    ("seed_chair.png", "Office chair", "Goods"),
    ("seed_monitor.png", "27in monitor", "Electronics"),
    ("seed_boxes.png", "Free boxes", "Goods"),
    ("seed_assembly.png", "Assembly svc", "Services"),
    ("seed_nursing.png", "Nursing books", "Textbook"),
    ("seed_helmet.png", "Helmet + lights", "Transport"),
    ("seed_bookshelf.png", "Bookshelf", "Goods"),
    ("seed_headphones.png", "Headphones", "Electronics"),
]

W, H = 640, 480
UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "uploads", "listings")
)


def draw(filename, label, category):
    top, bottom = COLORS.get(category, ("#5a5a5a", "#222222"))

    img = Image.new("RGB", (W, H), top)
    draw = ImageDraw.Draw(img)

    # Create a vertical gradient background.
    rgb_top = tuple(int(top[i:i + 2], 16) for i in (1, 3, 5))
    rgb_bottom = tuple(int(bottom[i:i + 2], 16) for i in (1, 3, 5))

    for y in range(H):
        blend = y / H
        rgb = tuple(
            int(rgb_top[i] + (rgb_bottom[i] - rgb_top[i]) * blend)
            for i in range(3)
        )
        draw.line([(0, y), (W, y)], fill=rgb)

    # Add the listing label and category.
    draw.rectangle([40, 150, W - 40, H - 150], fill=(255, 255, 255))
    draw.text((60, 170), label, fill=(20, 56, 95))
    draw.text(
        (60, 230),
        f"{category} - UoN Student Marketplace",
        fill=(110, 120, 130),
    )
    draw.text((60, 260), "Demo placeholder photo", fill=(150, 155, 160))

    img.save(os.path.join(UPLOAD_DIR, filename))


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    for item in IMAGES:
        draw(*item)

    print(
        f"Generated {len(IMAGES)} seed images in {UPLOAD_DIR}"
    )
