"""Giải mã ảnh tải lên và ảnh Canvas theo cùng một quy trình cho các mô hình thị giác."""
import base64
import binascii
import io

from PIL import Image,ImageOps,UnidentifiedImageError


def load_grayscale_image(image_input):
    try:
        # Canvas gửi chuỗi Base64, còn ảnh tải lên được chuyển vào dưới dạng byte.
        if isinstance(image_input,str):
            content=base64.b64decode(image_input.split(',',1)[-1],validate=True)
        elif isinstance(image_input,(bytes,bytearray)):
            content=image_input
        else:
            raise ValueError('Unsupported image input')
        with Image.open(io.BytesIO(content)) as original:
            # Áp dụng hướng ảnh từ EXIF trước khi chuyển hệ màu.
            original=ImageOps.exif_transpose(original)
            # Ghép vùng trong suốt lên nền trắng trước khi chuyển sang ảnh xám.
            if original.mode in ('RGBA','LA') or 'transparency' in original.info:
                rgba=original.convert('RGBA')
                original=Image.alpha_composite(Image.new('RGBA',rgba.size,'white'),rgba)
            return original.convert('L')
    except (binascii.Error,UnidentifiedImageError,OSError,ValueError) as error:
        raise ValueError('Không đọc được ảnh. Hãy chọn ảnh PNG/JPG hợp lệ hoặc vẽ lại trên bảng.') from error
