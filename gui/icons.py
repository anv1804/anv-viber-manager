"""
gui/icons.py
Dynamically generates clean, high-resolution PNG icon images in-memory
using PIL (Pillow) so the application does not depend on system fonts or external files.
Works perfectly on both Windows and Linux.
"""
from PIL import Image, ImageDraw


def _create_base_image(width=16, height=16, bg_color=(0, 0, 0, 0)):
    """Create a transparent base RGBA image and draw context."""
    img = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    return img, draw


def get_user_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Draw head
    draw.ellipse([5, 2, 11, 8], fill=color)
    # Draw shoulder
    draw.chord([2, 9, 14, 15], start=180, end=360, fill=color)
    return img


def get_key_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Key ring
    draw.ellipse([2, 4, 8, 10], outline=color, width=2)
    # Key stem
    draw.rectangle([8, 6, 14, 8], fill=color)
    # Key teeth
    draw.rectangle([11, 8, 12, 11], fill=color)
    draw.rectangle([13, 8, 14, 11], fill=color)
    return img


def get_logout_icon(color=(240, 76, 76, 255)):
    img, draw = _create_base_image(16, 16)
    # Door outline
    draw.line([(3, 2), (10, 2), (10, 14), (3, 14)], fill=color, width=2)
    # Arrow out
    draw.line([(6, 8), (14, 8)], fill=color, width=2)
    draw.line([(11, 5), (14, 8), (11, 11)], fill=color, width=2)
    return img


def get_create_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Plus sign
    draw.rectangle([7, 2, 9, 14], fill=color)
    draw.rectangle([2, 7, 14, 9], fill=color)
    return img


def get_delete_icon(color=(240, 76, 76, 255)):
    img, draw = _create_base_image(16, 16)
    # X sign
    draw.line([(3, 3), (13, 13)], fill=color, width=2)
    draw.line([(13, 3), (3, 13)], fill=color, width=2)
    return img


def get_export_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Box tray
    draw.line([(2, 11), (2, 14), (14, 14), (14, 11)], fill=color, width=2)
    # Arrow up
    draw.line([(8, 3), (8, 11)], fill=color, width=2)
    draw.line([(5, 6), (8, 3), (11, 6)], fill=color, width=2)
    return img


def get_import_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Box tray
    draw.line([(2, 11), (2, 14), (14, 14), (14, 11)], fill=color, width=2)
    # Arrow down
    draw.line([(8, 3), (8, 11)], fill=color, width=2)
    draw.line([(5, 8), (8, 11), (11, 8)], fill=color, width=2)
    return img


def _hex_to_rgba(color_val, alpha=255):
    """Convert hex string (e.g. #FFFFFF or #FFF) to RGBA tuple."""
    if isinstance(color_val, tuple):
        return color_val
    if isinstance(color_val, str) and color_val.startswith("#"):
        h = color_val.lstrip("#")
        if len(h) == 3:
            h = "".join(c*2 for c in h)
        if len(h) == 6:
            rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            return (rgb[0], rgb[1], rgb[2], alpha)
    return (160, 160, 160, alpha)


def get_users_icon(color=(115, 96, 222, 255)):
    img, draw = _create_base_image(16, 16)
    c_rgba = _hex_to_rgba(color, 255)
    c_semi = _hex_to_rgba(color, 180)
    # Draw user 1 (left/back)
    draw.ellipse([3, 3, 8, 8], fill=c_semi)
    draw.chord([1, 9, 10, 14], start=180, end=360, fill=c_semi)
    # Draw user 2 (right/front)
    draw.ellipse([8, 4, 13, 9], fill=c_rgba)
    draw.chord([6, 10, 15, 15], start=180, end=360, fill=c_rgba)
    return img


def get_sync_icon(color=(255, 255, 255, 255)):
    img, draw = _create_base_image(16, 16)
    # Circular arrows
    draw.arc([2, 2, 14, 14], start=45, end=315, fill=color, width=2)
    # Arrow heads
    draw.polygon([(11, 3), (14, 5), (14, 2)], fill=color)
    return img


def get_folder_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Folder body
    draw.polygon([(2, 3), (6, 3), (8, 5), (14, 5), (14, 13), (2, 13)], fill=color)
    return img


def get_search_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Loop magnifier
    draw.ellipse([2, 2, 10, 10], outline=color, width=2)
    # Handle
    draw.line([(9, 9), (14, 14)], fill=color, width=2)
    return img


def get_checkbox_unchecked(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    draw.rectangle([2, 2, 14, 14], outline=color, width=2)
    return img


def get_checkbox_checked(color=(115, 96, 222, 255)):
    img, draw = _create_base_image(16, 16)
    draw.rectangle([2, 2, 14, 14], outline=color, width=2)
    # Checkmark inside
    draw.line([(5, 8), (7, 11), (12, 4)], fill=color, width=2)
    return img


def get_play_icon(color=(255, 255, 255, 255)):
    img, draw = _create_base_image(16, 16)
    draw.polygon([(4, 3), (13, 8), (4, 13)], fill=color)
    return img


def get_stop_icon(color=(255, 255, 255, 255)):
    img, draw = _create_base_image(16, 16)
    draw.rectangle([4, 4, 12, 12], fill=color)
    return img


def get_edit_icon(color=(160, 160, 160, 255)):
    img, draw = _create_base_image(16, 16)
    # Pencil angle box
    draw.line([(3, 13), (13, 3)], fill=color, width=2)
    draw.line([(5, 14), (14, 5)], fill=color, width=2)
    # Tip
    draw.polygon([(2, 14), (2, 11), (5, 14)], fill=color)
    return img


def get_trash_icon(color=(240, 76, 76, 255)):
    img, draw = _create_base_image(16, 16)
    # Lid
    draw.line([(2, 3), (14, 3)], fill=color, width=2)
    draw.rectangle([6, 1, 10, 3], outline=color, width=1)
    # Body
    draw.rectangle([4, 4, 12, 14], outline=color, width=2)
    # Vertical lines
    draw.line([(6, 6), (6, 12)], fill=color, width=1)
    draw.line([(10, 6), (10, 12)], fill=color, width=1)
    return img
