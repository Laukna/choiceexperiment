from PIL import Image, ImageDraw
import os

# Path to your local background image
background_path = "choicedesign/Background.png"
# Folder to save images
output_folder = "choicedesign/door_images"
os.makedirs(output_folder, exist_ok=True)

def compose_image(D2D_value):
    base = Image.open(background_path).convert("RGBA")

    if D2D_value == 0:
        door_size_x, door_size_y, door_x, door_y = 700, 1000, 1900, 600
        front_width= 18
    elif D2D_value == 10:
        door_size_x, door_size_y, door_x, door_y = 350, 600, 1050, 700
        front_width= 16
    elif D2D_value == 30:
        door_size_x, door_size_y, door_x, door_y = 120, 300, 550, 800
        front_width= 12 
    elif D2D_value == 70:
        door_size_x, door_size_y, door_x, door_y = 60, 150, 290, 870
        front_width= 8 
    else:
        door_size_x, door_size_y = 400, 600
        door_x = int(1900 - D2D_value * 20)
        door_y = int(700 - D2D_value * 2)

    draw = ImageDraw.Draw(base)
    draw.rectangle(
        [(door_x, door_y), (door_x + door_size_x, door_y + door_size_y)],
        outline="yellow", width=front_width
    )
    return base

# Generate and save
for d2d in [0, 10, 30, 70]:
    img = compose_image(d2d)
#    filename = f"door_d2d_{d2d}.png"
#    img.save(os.path.join(output_folder, filename))
#    print(f"✅ Saved: {filename}")
