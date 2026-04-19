"""
富文本编辑器控件

提供富文本编辑功能，支持文字格式化和图片粘贴，点击图片可放大预览
"""
import os
import base64
import io
import re
from typing import Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QDialog,
    QLineEdit, QLabel, QApplication
)
from PySide6.QtCore import Signal, Qt, QMimeData, QEvent, QPoint
from PySide6.QtGui import (
    QTextCursor, QFont, QImage, QClipboard,
    QAction, QKeySequence, QShortcut, QKeyEvent,
    QTextDocumentFragment, QTextFormat
)

from ...data.image_manager import ImageManager
from ...data.clipboard_image import get_clipboard_image_bytes
from .image_preview import ImagePreviewDialog


class InsertLinkDialog(QDialog):
    """插入链接对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插入链接")
        self.setFixedSize(400, 150)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # URL输入
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("链接地址:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # 文本输入
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("显示文本:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("链接文字")
        text_layout.addWidget(self.text_input)
        layout.addLayout(text_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def get_result(self) -> tuple[str, str]:
        """获取输入结果"""
        return self.url_input.text(), self.text_input.text()


class RichTextEditor(QWidget):
    """
    富文本编辑器控件

    功能：
    - 文字格式化（粗体、斜体、下划线）
    - 图片粘贴和插入
    - 链接插入
    - 代码块插入
    - 内容获取与设置
    """

    # 信号定义
    content_changed = Signal(str)      # 内容变更信号
    image_inserted = Signal(str)       # 图片插入信号（图片路径）

    def __init__(self, parent=None, placeholder: str = "请输入内容...",
                 issue_no: str = None, read_only: bool = False):
        """
        初始化编辑器

        Args:
            parent: 父控件
            placeholder: 占位提示文字
            issue_no: 问题单号（用于图片存储）
            read_only: 是否只读模式
        """
        super().__init__(parent)
        self._placeholder = placeholder
        self._issue_no = issue_no or "temp"
        self._read_only = read_only
        self._image_manager = ImageManager()

        self.setup_ui()
        self.setup_style()

        # 安装事件过滤器到编辑器，用于拦截粘贴事件
        self._editor.installEventFilter(self)

        if read_only:
            self.set_read_only(True)

    def setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        self._toolbar = QWidget()
        self._toolbar.setObjectName("toolbar")
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(6, 4, 6, 4)
        toolbar_layout.setSpacing(2)

        # 粗体按钮
        self._bold_btn = QPushButton("B")
        self._bold_btn.setObjectName("toolBtn")
        self._bold_btn.setToolTip("粗体 (Ctrl+B)")
        self._bold_btn.setCheckable(True)
        self._bold_btn.clicked.connect(self.on_bold)
        toolbar_layout.addWidget(self._bold_btn)

        # 斜体按钮
        self._italic_btn = QPushButton("I")
        self._italic_btn.setObjectName("toolBtn")
        self._italic_btn.setToolTip("斜体 (Ctrl+I)")
        self._italic_btn.setCheckable(True)
        self._italic_btn.clicked.connect(self.on_italic)
        toolbar_layout.addWidget(self._italic_btn)

        # 下划线按钮
        self._underline_btn = QPushButton("U")
        self._underline_btn.setObjectName("toolBtn")
        self._underline_btn.setToolTip("下划线 (Ctrl+U)")
        self._underline_btn.setCheckable(True)
        self._underline_btn.clicked.connect(self.on_underline)
        toolbar_layout.addWidget(self._underline_btn)

        toolbar_layout.addWidget(self._create_separator())

        # 插入图片按钮
        self._image_btn = QPushButton("📷")
        self._image_btn.setObjectName("toolBtn")
        self._image_btn.setToolTip("插入图片")
        self._image_btn.clicked.connect(self.on_insert_image)
        toolbar_layout.addWidget(self._image_btn)

        # 插入链接按钮
        self._link_btn = QPushButton("🔗")
        self._link_btn.setObjectName("toolBtn")
        self._link_btn.setToolTip("插入链接")
        self._link_btn.clicked.connect(self.on_insert_link)
        toolbar_layout.addWidget(self._link_btn)

        toolbar_layout.addWidget(self._create_separator())

        # 清除格式按钮
        self._clear_btn = QPushButton("清除")
        self._clear_btn.setObjectName("toolBtn")
        self._clear_btn.setToolTip("清除格式")
        self._clear_btn.clicked.connect(self.on_clear_format)
        toolbar_layout.addWidget(self._clear_btn)

        toolbar_layout.addStretch()

        layout.addWidget(self._toolbar)

        # 编辑区域
        self._editor = QTextEdit()
        self._editor.setPlaceholderText(self._placeholder)
        self._editor.setAcceptRichText(True)
        self._editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._editor)

        # 设置编辑器高度
        self._min_height = 200  # 默认最小高度
        self._editor.setMinimumHeight(self._min_height)

    def _create_separator(self) -> QWidget:
        """创建分隔线"""
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #3E3E4E;")
        return separator

    def setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            RichTextEditor {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
            }

            QWidget#toolbar {
                background-color: #1E1E2E;
                border-bottom: 1px solid #3E3E4E;
                border-radius: 8px 8px 0 0;
            }

            QPushButton#toolBtn {
                background-color: #3E3E4E;
                border: none;
                border-radius: 3px;
                padding: 4px 6px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                min-width: 24px;
                max-width: 24px;
            }

            QPushButton#toolBtn:hover {
                background-color: #4E4E5E;
            }

            QPushButton#toolBtn:checked {
                background-color: #3498DB;
            }

            QTextEdit {
                background-color: #2E2E3E;
                border: none;
                color: #FFFFFF;
                font-size: 14px;
                padding: 12px;
                border-radius: 0 0 8px 8px;
            }

            QTextEdit:focus {
                border: none;
                outline: none;
            }
        """)

    def eventFilter(self, obj, event):
        """事件过滤器，用于拦截粘贴事件和图片点击事件"""
        if obj == self._editor:
            # 处理键盘事件（粘贴）
            if event.type() == QEvent.KeyPress:
                key_event = event
                if key_event.key() == Qt.Key_V and (key_event.modifiers() & Qt.ControlModifier):
                    self._on_custom_paste()
                    return True

            # 处理鼠标点击事件（图片预览）
            if event.type() == QEvent.MouseButtonPress:
                mouse_event = event
                if mouse_event.button() == Qt.LeftButton:
                    # 检查点击位置是否有图片
                    self._check_image_click(mouse_event.pos())

        return super().eventFilter(obj, event)

    def _check_image_click(self, pos: QPoint):
        """检查点击位置是否是图片"""
        # 获取点击位置的文档位置
        cursor = self._editor.cursorForPosition(pos)
        char_format = cursor.charFormat()

        # 检查是否是图片
        if char_format.isImageFormat():
            # 获取图片名称
            image_name = char_format.stringProperty(QTextFormat.ImageName)
            if image_name:
                self._show_image_preview(image_name)

    def _show_image_preview(self, image_path: str):
        """显示图片预览"""
        dialog = ImagePreviewDialog(image_path, self)
        dialog.exec()

    def _on_custom_paste(self):
        """自定义粘贴处理"""
        # 先尝试使用PIL获取剪贴板图片（支持Snipaste等工具）
        image_data = get_clipboard_image_bytes()
        if image_data:
            self._insert_image_data_direct(image_data)
            return

        # 再尝试Qt方式
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        # 检查是否有图片（Qt标准方式）
        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                self._insert_qimage(image)
                return

        # 检查是否有文件URL（可能是图片文件）
        if mime_data.hasUrls():
            urls = mime_data.urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}:
                        self.insert_image_from_file(file_path)
                        return

        # 检查是否有HTML内容（可能包含base64图片）
        if mime_data.hasHtml():
            html = mime_data.html()
            if 'base64' in html and 'image' in html:
                self._extract_and_insert_base64_images(html)
                return

        # 默认粘贴文本
        self._editor.paste()

    def _insert_image_data_direct(self, image_data: bytes):
        """直接插入图片字节数据"""
        try:
            # 保存图片
            relative_path = self._image_manager.save_image(image_data, self._issue_no)
            absolute_path = self._image_manager.get_absolute_path(relative_path)

            # 插入HTML
            html = f'<img src="{absolute_path}" style="max-width: 600px; display: block; margin: 10px auto;">'
            cursor = self._editor.textCursor()
            cursor.insertHtml(html)

            self.image_inserted.emit(relative_path)
        except Exception as e:
            QMessageBox.warning(self, "插入图片失败", str(e))

    def _extract_and_insert_base64_images(self, html: str):
        """从HTML中提取base64图片并插入"""
        import re
        # 匹配base64图片
        pattern = re.compile(r'data:image/(png|jpeg|jpg|gif|webp);base64,([A-Za-z0-9+/=]+)', re.IGNORECASE)

        for match in pattern.finditer(html):
            mime_type = match.group(1)
            base64_data = match.group(2)

            try:
                image_data = base64.b64decode(base64_data)
                self._insert_image_data_direct(image_data)
            except Exception:
                pass

    def _on_text_changed(self):
        """文本变更事件"""
        html = self.get_html_content()
        self.content_changed.emit(html)

    # ========== 工具栏操作 ==========

    def on_bold(self):
        """粗体操作"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            char_format = cursor.charFormat()
            if char_format.fontWeight() == QFont.Bold:
                char_format.setFontWeight(QFont.Normal)
            else:
                char_format.setFontWeight(QFont.Bold)
            cursor.mergeCharFormat(char_format)

    def on_italic(self):
        """斜体操作"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            char_format = cursor.charFormat()
            char_format.setFontItalic(self._italic_btn.isChecked())
            cursor.mergeCharFormat(char_format)

    def on_underline(self):
        """下划线操作"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            char_format = cursor.charFormat()
            char_format.setFontUnderline(self._underline_btn.isChecked())
            cursor.mergeCharFormat(char_format)

    def on_insert_image(self):
        """插入图片（文件选择）"""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("选择图片")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)")

        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                self.insert_image_from_file(file_paths[0])

    def on_insert_link(self):
        """插入链接"""
        dialog = InsertLinkDialog(self)
        if dialog.exec():
            url, text = dialog.get_result()
            if url:
                if not text:
                    text = url
                html = f'<a href="{url}" style="color: #3498DB;">{text}</a>'
                cursor = self._editor.textCursor()
                cursor.insertHtml(html)

    def on_clear_format(self):
        """清除格式"""
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(QTextCharFormat())
            cursor.clearSelection()

    # ========== 图片处理 ==========

    def _insert_qimage(self, image: QImage):
        """插入QImage对象"""
        # 转换为字节数据
        byte_array = image.toByteArray()
        image_data = bytes(byte_array.data())

        # 保存图片
        relative_path = self._image_manager.save_image(image_data, self._issue_no)
        absolute_path = self._image_manager.get_absolute_path(relative_path)

        # 插入HTML
        html = f'<img src="{absolute_path}" style="max-width: 600px; display: block; margin: 10px auto;">'
        cursor = self._editor.textCursor()
        cursor.insertHtml(html)

        self.image_inserted.emit(relative_path)

    def insert_image_from_file(self, file_path: str):
        """从文件插入图片"""
        try:
            relative_path = self._image_manager.save_image_from_file(file_path, self._issue_no)
            absolute_path = self._image_manager.get_absolute_path(relative_path)

            html = f'<img src="{absolute_path}" style="max-width: 600px; display: block; margin: 10px auto;">'
            cursor = self._editor.textCursor()
            cursor.insertHtml(html)

            self.image_inserted.emit(relative_path)
        except Exception as e:
            QMessageBox.warning(self, "插入图片失败", str(e))

    def insert_image_data(self, image_data: bytes):
        """插入图片二进制数据"""
        try:
            relative_path = self._image_manager.save_image(image_data, self._issue_no)
            absolute_path = self._image_manager.get_absolute_path(relative_path)

            html = f'<img src="{absolute_path}" style="max-width: 600px; display: block; margin: 10px auto;">'
            cursor = self._editor.textCursor()
            cursor.insertHtml(html)

            self.image_inserted.emit(relative_path)
        except Exception as e:
            QMessageBox.warning(self, "插入图片失败", str(e))

    # ========== 内容操作 ==========

    def get_html_content(self) -> str:
        """获取HTML内容"""
        return self._editor.toHtml()

    def set_html_content(self, html: str):
        """设置HTML内容"""
        # 将相对路径转换为绝对路径用于显示
        processed_html = self._image_manager.convert_to_absolute_paths(html)
        self._editor.setHtml(processed_html)

    def get_plain_text(self) -> str:
        """获取纯文本内容"""
        return self._editor.toPlainText()

    def set_plain_text(self, text: str):
        """设置纯文本内容"""
        self._editor.setPlainText(text)

    def clear_content(self):
        """清空内容"""
        self._editor.clear()

    def is_empty(self) -> bool:
        """检查内容是否为空"""
        return self._editor.toPlainText().strip() == ""

    # ========== 辅助方法 ==========

    def set_placeholder(self, text: str):
        """设置占位文字"""
        self._placeholder = text
        self._editor.setPlaceholderText(text)

    def set_read_only(self, read_only: bool):
        """设置只读模式"""
        self._read_only = read_only
        self._editor.setReadOnly(read_only)
        self._toolbar.setVisible(not read_only)

    def set_min_height(self, height: int):
        """设置最小高度"""
        self._min_height = height
        self._editor.setMinimumHeight(height)

    def set_adaptive_height(self, min_height: int = 120, max_height: int = 800):
        """
        设置自适应高度（根据内容自动调整）

        Args:
            min_height: 最小高度
            max_height: 最大高度
        """
        self._min_height = min_height
        self._editor.setMinimumHeight(min_height)

        # 获取文档内容的实际高度
        document = self._editor.document()
        document.setTextWidth(self._editor.width())

        # 计算内容高度（加上padding）
        content_height = int(document.size().height()) + 40  # 加上padding

        # 在最小高度和最大高度之间取值
        actual_height = max(min_height, min(content_height, max_height))

        self._editor.setMinimumHeight(actual_height)
        self._editor.setMaximumHeight(actual_height)

    def set_issue_no(self, issue_no: str):
        """设置问题单号"""
        self._issue_no = issue_no

    def focus_editor(self):
        """聚焦编辑器"""
        self._editor.setFocus()


class QTextCharFormat:
    """文本字符格式（辅助类）"""
    pass