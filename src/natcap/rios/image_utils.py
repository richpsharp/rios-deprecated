import PIL
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw


def write_splash_screen(base_image, font_path, version, out_path):
    """Write a simple splash screen by compositing text on top of a base image.

    base_image - a uri to an image
    font_path - a uri to a truetype font file
    version - the version string to write to the splash screen
    out_path - the output path to the finished file

    returns nothing."""

    font = ImageFont.truetype(font_path, 25)
    img = Image.open(base_image)
    draw = ImageDraw.Draw(img)
    draw.text((15,375), version, (150,150,150), font=font)

    draw = ImageDraw.Draw(img)
    img.save(out_path)
