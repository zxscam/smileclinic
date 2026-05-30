from PIL import Image, ImageDraw, ImageFont
import os

def create_image(filename, size, bg_color, text="", text_color=(255,255,255)):
    """Создаёт минималистичное изображение"""
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    if text:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 36)
            except:
                font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (size[0] - tw) // 2, (size[1] - th) // 2
        draw.text((x, y), text, fill=text_color, font=font)
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename)
    print(f"  ✓ {filename}")

base = "static/images/"
blue = (37, 99, 235)
light_blue = (219, 234, 254)
dark_blue = (30, 64, 175)
gray = (100, 116, 139)

print("Создание изображений для SmileClinic...")

# Логотип
create_image(f"{base}logo.png", (200, 200), blue, "SC", (255, 255, 255))

# Фавикон
create_image(f"{base}favicon.ico", (32, 32), blue)

# Герой
create_image(f"{base}hero-bg.jpg", (1200, 600), light_blue)

# Клиника
for i in range(1, 4):
    create_image(f"{base}clinic-{i}.jpg", (800, 500), light_blue, f"SmileClinic {i}", blue)

# Врачи
for i in range(1, 4):
    create_image(f"{base}doctor-{i}.jpg", (400, 400), light_blue, f"Doctor {i}", blue)
create_image(f"{base}doctor-default.jpg", (400, 400), gray, "Doctor", (255,255,255))

# Услуги
service_names = ["Консультация", "Кариес", "Чистка", "Удаление", "Брекеты", "Отбеливание"]
service_files = ["consult", "caries", "cleaning", "extraction", "braces", "whitening"]
for fname, sname in zip(service_files, service_names):
    create_image(f"{base}service-{fname}.jpg", (600, 400), light_blue, sname, blue)

# Акции
for i in range(1, 5):
    create_image(f"{base}promo-{i}.jpg", (800, 400), light_blue, f"Акция {i}", blue)

print("\nГотово! Запустите: python app.py")