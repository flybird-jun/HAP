"""
图片预览对话框

点击图片时弹出放大显示
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage


class ImagePreviewDialog(QDialog):
    """
    图片预览对话框

    功能：
    - 点击图片时弹出放大显示
    - 支持滚动查看大图
    """

    def __init__(self, image_path: str, parent=None):
        """
        初始化图片预览对话框

        Args:
            image_path: 图片路径（可以是绝对路径或相对路径）
            parent: 父窗口
        """
        super().__init__(parent)

        self._image_path = image_path

        self.setWindowTitle("图片预览")
        self.setMinimumSize(400, 300)
        self.resize(800, 600)

        self.setup_ui()
        self.setup_style()
        self.load_image()

    def setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)

        # 图片标签
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("background-color: #1E1E2E;")

        scroll.setWidget(self._image_label)
        layout.addWidget(scroll)

    def setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E2E;
            }

            QScrollArea {
                background-color: #1E1E2E;
                border: none;
            }

            QLabel {
                background-color: #1E1E2E;
            }
        """)

    def load_image(self):
        """加载图片"""
        # 处理路径
        if not os.path.isabs(self._image_path):
            # 相对路径，转换为绝对路径
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self._image_path = os.path.join(base_dir, self._image_path)

        if os.path.exists(self._image_path):
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                # 缩放图片以适应窗口，但保持比例
                screen_size = self.size()
                max_width = screen_size.width() - 20
                max_height = screen_size.height() - 20

                if pixmap.width() > max_width or pixmap.height() > max_height:
                    scaled_pixmap = pixmap.scaled(
                        max_width, max_height,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self._image_label.setPixmap(scaled_pixmap)
                else:
                    self._image_label.setPixmap(pixmap)
            else:
                self._image_label.setText("无法加载图片")
        else:
            self._image_label.setText(f"图片不存在: {self._image_path}")

    def mousePressEvent(self, event):
        """鼠标点击事件 - 点击任意位置关闭"""
        self.close()

    def keyPressEvent(self, event):
        """键盘事件 - ESC或空格关闭"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_Space:
            self.close()