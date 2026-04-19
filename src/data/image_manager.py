"""
图片存储管理模块

负责图片的本地存储、路径管理、图片删除等操作
"""
import os
import re
import base64
import uuid
import time
import random
import string
import sys
import shutil
from typing import Optional, Tuple


def get_data_path(relative_path):
    """获取数据文件的绝对路径（持久化目录）"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后，数据文件放在 exe 所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


class ImageManager:
    """
    图片管理器

    功能：
    - 图片本地存储
    - 图片路径管理
    - 图片删除清理
    - HTML内容中图片提取与处理
    """

    # 图片存储根目录
    IMAGE_DIR = "images"

    # 支持的图片格式
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

    # Base64图片匹配正则
    BASE64_IMG_PATTERN = re.compile(
        r'<img[^>]+src="data:image/(png|jpeg|jpg|gif|bmp|webp);base64,([^"]+)"[^>]*>',
        re.IGNORECASE
    )

    DATA_URL_PATTERN = re.compile(
        r'^data:image/(png|jpeg|jpg|gif|bmp|webp);base64,(.+)$',
        re.IGNORECASE
    )

    def __init__(self, base_path: str = None):
        """
        初始化图片管理器

        Args:
            base_path: 应用根目录路径，默认为当前目录
        """
        if base_path is None:
            # 获取项目根目录（支持打包后运行）
            base_path = get_data_path('')

        self._base_path = base_path
        self._image_dir = os.path.join(base_path, self.IMAGE_DIR)

        # 确保图片目录存在
        os.makedirs(self._image_dir, exist_ok=True)

    def get_image_dir(self, issue_no: str) -> str:
        """
        获取指定问题单的图片目录

        Args:
            issue_no: 问题单号

        Returns:
            图片目录完整路径
        """
        issue_dir = os.path.join(self._image_dir, issue_no)
        os.makedirs(issue_dir, exist_ok=True)
        return issue_dir

    def generate_filename(self, extension: str = '.png') -> str:
        """
        生成唯一文件名

        Args:
            extension: 文件扩展名

        Returns:
            格式为 timestamp_random.ext 的文件名
        """
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{timestamp}_{random_str}{extension.lower()}"

    def save_image(self, image_data: bytes, issue_no: str, filename: str = None) -> str:
        """
        保存图片到本地

        Args:
            image_data: 图片二进制数据
            issue_no: 问题单号
            filename: 自定义文件名，不指定则自动生成

        Returns:
            图片相对路径（相对于应用根目录）
        """
        if not image_data:
            raise ValueError("图片数据为空")

        # 获取图片目录
        issue_dir = self.get_image_dir(issue_no)

        # 生成文件名
        if filename is None:
            filename = self.generate_filename('.png')

        # 确保文件名合法
        if not filename.lower().endswith(tuple(self.SUPPORTED_FORMATS)):
            filename += '.png'

        # 构建完整路径
        file_path = os.path.join(issue_dir, filename)

        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(image_data)

        # 返回相对路径
        return os.path.join(self.IMAGE_DIR, issue_no, filename)

    def save_image_from_file(self, source_path: str, issue_no: str) -> str:
        """
        从文件保存图片

        Args:
            source_path: 源文件路径
            issue_no: 问题单号

        Returns:
            图片相对路径
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"源文件不存在: {source_path}")

        # 检查文件格式
        ext = os.path.splitext(source_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持图片格式: {ext}")

        # 读取文件
        with open(source_path, 'rb') as f:
            image_data = f.read()

        # 生成文件名
        filename = self.generate_filename(ext)

        return self.save_image(image_data, issue_no, filename)

    def delete_image(self, relative_path: str) -> bool:
        """
        删除图片

        Args:
            relative_path: 图片相对路径

        Returns:
            删除是否成功
        """
        absolute_path = self.get_absolute_path(relative_path)

        if not os.path.exists(absolute_path):
            return False

        try:
            os.remove(absolute_path)
            return True
        except Exception:
            return False

    def delete_issue_images(self, issue_no: str) -> int:
        """
        删除指定问题单的所有图片

        Args:
            issue_no: 问题单号

        Returns:
            删除的图片数量
        """
        issue_dir = self.get_image_dir(issue_no)

        if not os.path.exists(issue_dir):
            return 0

        count = 0
        try:
            # 统计文件数
            for filename in os.listdir(issue_dir):
                file_path = os.path.join(issue_dir, filename)
                if os.path.isfile(file_path):
                    count += 1

            # 删除目录
            shutil.rmtree(issue_dir)
        except Exception:
            pass

        return count

    def get_absolute_path(self, relative_path: str) -> str:
        """
        获取图片绝对路径

        Args:
            relative_path: 图片相对路径

        Returns:
            图片绝对路径
        """
        return os.path.join(self._base_path, relative_path)

    def image_exists(self, relative_path: str) -> bool:
        """
        检查图片是否存在

        Args:
            relative_path: 图片相对路径

        Returns:
            图片是否存在
        """
        absolute_path = self.get_absolute_path(relative_path)
        return os.path.exists(absolute_path)

    def extract_images_from_html(self, html_content: str, issue_no: str) -> str:
        """
        从HTML内容中提取base64图片并保存

        Args:
            html_content: HTML内容
            issue_no: 问题单号

        Returns:
            处理后的HTML内容（base64替换为本地路径）
        """
        if not html_content:
            return html_content

        def replace_base64_img(match):
            """替换base64图片标签"""
            mime_type = match.group(1).lower()
            base64_data = match.group(2)

            try:
                # 解码base64数据
                image_data = base64.b64decode(base64_data)

                # 确定扩展名
                ext_map = {
                    'png': '.png',
                    'jpeg': '.jpg',
                    'jpg': '.jpg',
                    'gif': '.gif',
                    'bmp': '.bmp',
                    'webp': '.webp'
                }
                ext = ext_map.get(mime_type, '.png')

                # 保存图片
                filename = self.generate_filename(ext)
                relative_path = self.save_image(image_data, issue_no, filename)

                # 构建新的img标签
                absolute_path = self.get_absolute_path(relative_path)
                return f'<img src="{absolute_path}" style="max-width: 600px; display: block; margin: 10px auto;">'
            except Exception:
                # 如果处理失败，保留原始标签
                return match.group(0)

        # 替换所有base64图片
        processed_html = self.BASE64_IMG_PATTERN.sub(replace_base64_img, html_content)

        return processed_html

    def get_image_info(self, relative_path: str) -> dict:
        """
        获取图片信息

        Args:
            relative_path: 图片相对路径

        Returns:
            包含宽度、高度、大小等信息的字典
        """
        absolute_path = self.get_absolute_path(relative_path)

        if not os.path.exists(absolute_path):
            return {}

        info = {
            'path': relative_path,
            'size': os.path.getsize(absolute_path)
        }

        # 尝试获取图片尺寸（需要PIL）
        try:
            from PIL import Image
            with Image.open(absolute_path) as img:
                info['width'] = img.width
                info['height'] = img.height
        except ImportError:
            pass

        return info

    def convert_to_absolute_paths(self, html_content: str) -> str:
        """
        将HTML中的相对图片路径转换为绝对路径

        Args:
            html_content: HTML内容

        Returns:
            转换后的HTML内容
        """
        if not html_content:
            return html_content

        def replace_relative_path(match):
            """替换相对路径"""
            full_match = match.group(0)
            src = match.group(1)

            # 检查是否是相对路径（以images/开头）
            if src.startswith(self.IMAGE_DIR + '/') or src.startswith(self.IMAGE_DIR + '\\'):
                absolute_path = self.get_absolute_path(src)
                return full_match.replace(src, absolute_path)

            return full_match

        # 匹配img标签的src属性
        img_pattern = re.compile(r'<img[^>]+src="([^"]+)"[^>]*>')
        processed_html = img_pattern.sub(replace_relative_path, html_content)

        return processed_html

    def convert_to_relative_paths(self, html_content: str) -> str:
        """
        将HTML中的绝对图片路径转换为相对路径

        Args:
            html_content: HTML内容

        Returns:
            转换后的HTML内容
        """
        if not html_content:
            return html_content

        def replace_absolute_path(match):
            """替换绝对路径"""
            full_match = match.group(0)
            src = match.group(1)

            # 检查是否包含图片目录
            if self.IMAGE_DIR in src:
                # 提取相对路径部分
                idx = src.find(self.IMAGE_DIR)
                relative_path = src[idx:]
                return full_match.replace(src, relative_path)

            return full_match

        # 匹配img标签的src属性
        img_pattern = re.compile(r'<img[^>]+src="([^"]+)"[^>]*>')
        processed_html = img_pattern.sub(replace_absolute_path, html_content)

        return processed_html

    @property
    def base_path(self) -> str:
        """获取应用根目录"""
        return self._base_path

    @property
    def image_dir(self) -> str:
        """获取图片目录"""
        return self._image_dir