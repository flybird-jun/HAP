"""
剪贴板图片获取模块

使用Windows API获取剪贴板中的图片数据
"""
import ctypes
from ctypes import wintypes
import struct
import io

# Windows API 常量
CF_BITMAP = 2
CF_DIB = 8
CF_DIBV5 = 17
GMEM_MOVEABLE = 0x0002

# 加载Windows DLL
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32


def get_clipboard_image_bytes() -> bytes | None:
    """
    从剪贴板获取图片数据

    Returns:
        图片的PNG字节数据，如果没有图片则返回None
    """
    try:
        # 尝试使用PIL（最简单的方式）
        from PIL import ImageGrab, Image
        img = ImageGrab.grabclipboard()

        if img is not None and isinstance(img, Image.Image):
            # 转换为PNG字节
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()

        if img is not None and isinstance(img, list):
            # 可能是文件路径列表
            for path in img:
                if path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    with open(path, 'rb') as f:
                        return f.read()

        return None
    except Exception:
        return None


def get_clipboard_image_via_winapi() -> bytes | None:
    """
    使用Windows API直接获取剪贴板DIB数据

    Returns:
        图片的字节数据
    """
    try:
        if not user32.OpenClipboard(0):
            return None

        # 尝试获取DIB格式
        if user32.IsClipboardFormatAvailable(CF_DIB):
            handle = user32.GetClipboardData(CF_DIB)
            if handle:
                # 锁定内存获取数据
                ptr = kernel32.GlobalLock(handle)
                size = kernel32.GlobalSize(handle)

                if ptr and size:
                    # 读取数据
                    data = ctypes.string_at(ptr, size)
                    kernel32.GlobalUnlock(handle)

                    # 解析DIB数据并转换为PNG
                    return _convert_dib_to_png(data)

        user32.CloseClipboard()
        return None
    except Exception:
        user32.CloseClipboard()
        return None


def _convert_dib_to_png(dib_data: bytes) -> bytes | None:
    """
    将DIB数据转换为PNG

    Args:
        dib_data: DIB格式的图片数据

    Returns:
        PNG格式的图片数据
    """
    try:
        from PIL import Image
        import io

        # DIB数据结构: BITMAPINFOHEADER + 像素数据
        # 解析BITMAPINFOHEADER
        if len(dib_data) < 40:
            return None

        # 读取头信息
        bi_size = struct.unpack('<I', dib_data[0:4])[0]
        bi_width = struct.unpack('<i', dib_data[4:8])[0]
        bi_height = struct.unpack('<i', dib_data[8:12])[0]
        bi_planes = struct.unpack('<H', dib_data[12:14])[0]
        bi_bit_count = struct.unpack('<H', dib_data[14:16])[0]
        bi_compression = struct.unpack('<I', dib_data[16:20])[0]

        # 确定颜色模式
        if bi_bit_count == 24:
            mode = 'RGB'
        elif bi_bit_count == 32:
            mode = 'RGBA' if bi_compression == 0 else 'RGBX'
        else:
            # 其他格式，使用PIL的解析
            mode = None

        # 像素数据起始位置
        pixel_offset = bi_size
        if bi_bit_count <= 8:
            # 有调色板
            color_table_size = (1 << bi_bit_count) * 4
            pixel_offset += color_table_size

        pixel_data = dib_data[pixel_offset:]

        # DIB的高度是正数时，像素从下往上排列，需要翻转
        if bi_height > 0:
            # 创建图像并翻转
            stride = ((bi_width * bi_bit_count + 31) // 32) * 4
            if mode:
                img = Image.frombytes(mode, (bi_width, bi_height), pixel_data, 'raw', mode[::-1], stride)
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            else:
                return None
        else:
            # 高度为负数时，像素从上往下排列（正常顺序）
            bi_height = abs(bi_height)
            stride = ((bi_width * bi_bit_count + 31) // 32) * 4
            if mode:
                img = Image.frombytes(mode, (bi_width, bi_height), pixel_data, 'raw', mode[::-1], stride)
            else:
                return None

        # 转换为PNG
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    except Exception:
        return None


if __name__ == '__main__':
    # 测试
    data = get_clipboard_image_bytes()
    if data:
        print(f'获取图片成功，大小: {len(data)} bytes')
        with open('test_clipboard_api.png', 'wb') as f:
            f.write(data)
        print('保存到 test_clipboard_api.png')
    else:
        print('剪贴板中没有图片')