"""
问题单详情面板

展示问题单详情，根据状态提供不同的操作界面
（嵌入主界面使用，不是弹窗）
"""
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox,
    QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Signal, Qt

from ..data.database_manager import DatabaseManager
from ..data.issue_dao import IssueDAO
from ..data.module_dao import ModuleDAO
from ..data.project_dao import ProjectDAO
from ..models.issue_model import Issue, IssueStatus
from .widgets.rich_text_editor import RichTextEditor


class IssueDetailPanel(QWidget):
    """
    问题单详情面板

    功能：
    - 展示问题单详情
    - 根据状态提供不同的编辑界面
    - 处理提交和回退操作
    """

    # 信号定义
    issue_updated = Signal(int)  # 问题单更新成功信号
    issue_deleted = Signal(int)  # 问题单删除成功信号
    closed = Signal()            # 关闭面板信号

    def __init__(self, parent=None):
        """初始化面板"""
        super().__init__(parent)

        # 初始化数据访问对象
        self._db = DatabaseManager.get_instance()
        self._issue_dao = IssueDAO(self._db)
        self._module_dao = ModuleDAO(self._db)
        self._project_dao = ProjectDAO(self._db)

        # 问题单ID和数据
        self._issue_id: Optional[int] = None
        self._issue: Optional[Issue] = None

        self.setup_ui()
        self.setup_style()
        self.show_empty_state()

    def setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题栏
        title_bar = QHBoxLayout()

        self._title_label = QLabel("问题单详情")
        self._title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #3498DB;")
        title_bar.addWidget(self._title_label)

        title_bar.addStretch()

        self._close_btn = QPushButton("返回列表")
        self._close_btn.setObjectName("closePanelBtn")
        self._close_btn.clicked.connect(self._on_close)
        title_bar.addWidget(self._close_btn)

        layout.addLayout(title_bar)

        # 滚动内容区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setSpacing(10)
        scroll.setWidget(self._content_widget)

        layout.addWidget(scroll, stretch=1)

        # 底部按钮区域
        self._btn_layout = QHBoxLayout()
        self._btn_layout.addStretch()
        layout.addLayout(self._btn_layout)

    def setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            IssueDetailPanel {
                background-color: #1E1E2E;
                border: none;
            }

            QGroupBox {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 12px;
                margin-top: 20px;
                padding-top: 20px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 8px 16px;
                background-color: #3498DB;
                border-radius: 6px;
                margin-left: 10px;
            }

            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                outline: none;
            }

            QLabel:focus {
                outline: none;
                border: none;
            }

            QLineEdit {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                padding: 12px;
                color: #FFFFFF;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 2px solid #3498DB;
            }

            QGroupBox:focus {
                outline: none;
            }

            QComboBox {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                padding: 8px;
                color: #FFFFFF;
                min-width: 200px;
            }

            QComboBox::drop-down {
                border: none;
                width: 25px;
            }

            QComboBox QAbstractItemView {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                selection-background-color: #3498DB;
                color: #FFFFFF;
            }

            QPushButton {
                background-color: #3E3E4E;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                color: #FFFFFF;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #4E4E5E;
            }

            QPushButton#submitBtn {
                background-color: #27AE60;
                font-weight: bold;
            }

            QPushButton#submitBtn:hover {
                background-color: #2ECC71;
            }

            QPushButton#rollbackBtn {
                background-color: #E74C3C;
                font-weight: bold;
            }

            QPushButton#rollbackBtn:hover {
                background-color: #C0392B;
            }

            QPushButton#deleteBtn {
                background-color: #C0392B;
                font-weight: bold;
            }

            QPushButton#deleteBtn:hover {
                background-color: #A93226;
            }

            QPushButton#closePanelBtn {
                background-color: #3498DB;
            }

            QPushButton#closePanelBtn:hover {
                background-color: #2980B9;
            }
        """)

    def show_empty_state(self):
        """显示空状态"""
        self._title_label.setText("问题单详情")
        self._title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #888888;")

        # 清空内容
        self._clear_content()

        # 显示提示
        empty_label = QLabel("请从左侧列表选择问题单查看详情")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("font-size: 16px; color: #888888; padding: 50px;")
        self._content_layout.addWidget(empty_label)

    def load_issue(self, issue_id: int):
        """加载问题单"""
        self._issue_id = issue_id
        self._issue = self._issue_dao.get_by_id(issue_id)

        if self._issue:
            self._title_label.setText(f"问题单详情 - {self._issue.issue_no}")
            self._title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #3498DB;")
            self._update_ui_for_status()

    def _clear_content(self):
        """清空内容区域"""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 清空按钮区域
        while self._btn_layout.count():
            item = self._btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _update_ui_for_status(self):
        """根据状态更新UI"""
        if not self._issue:
            return

        self._clear_content()

        status = self._issue.status

        # 基本信息
        self._add_basic_info()

        # 根据状态添加不同内容
        if status == IssueStatus.SUBMIT_TEST:
            self._setup_submit_test_ui()
        elif status == IssueStatus.DEVELOPING:
            self._setup_developing_ui()
        elif status == IssueStatus.ARCHIVED:
            self._setup_archived_ui()
        elif status == IssueStatus.CLOSED:
            self._setup_closed_ui()

    def _add_basic_info(self):
        """添加基本信息"""
        group = QGroupBox("基本信息")
        layout = QVBoxLayout(group)

        # 问题单号
        issue_no_label = QLabel(f"问题单号: {self._issue.issue_no}")
        issue_no_label.setStyleSheet("font-weight: bold; color: #3498DB;")
        layout.addWidget(issue_no_label)

        # 所属项目
        project_name = self._issue.project_name or "未知"
        project_label = QLabel(f"所属项目: {project_name}")
        project_label.setStyleSheet("font-weight: bold; color: #27AE60;")
        layout.addWidget(project_label)

        # 状态和停留时间
        status_name = IssueStatus.get_name(self._issue.status)
        status_colors = {
            IssueStatus.SUBMIT_TEST: "#F5F5F5",
            IssueStatus.DEVELOPING: "#3498DB",
            IssueStatus.ARCHIVED: "#F1C40F",
            IssueStatus.CLOSED: "#2C3E50"
        }
        color = status_colors.get(self._issue.status, "#FFFFFF")

        status_row = QHBoxLayout()
        status_label = QLabel(f"当前状态: {status_name}")
        status_label.setStyleSheet(f"font-weight: bold; color: {color};")
        status_row.addWidget(status_label)
        status_row.addStretch()

        stay_duration = self._issue.calculate_stay_duration()
        stay_label = QLabel(f"停留时间: {stay_duration}")
        status_row.addWidget(stay_label)
        layout.addLayout(status_row)

        self._content_layout.addWidget(group)

    def _setup_submit_test_ui(self):
        """设置提交测试状态的UI"""
        # 简要描述可编辑
        title_group = QGroupBox("简要描述")
        title_layout = QVBoxLayout(title_group)
        self._title_input = QLineEdit()
        self._title_input.setText(self._issue.title)
        self._title_input.setMaxLength(100)
        title_layout.addWidget(self._title_input)
        self._content_layout.addWidget(title_group)

        # 详细描述可编辑
        self._description_editor = self._add_edit_section("详细描述", self._issue.description)

        self._content_layout.addStretch()

        # 按钮
        delete_btn = QPushButton("销毁问题单")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.clicked.connect(self._on_delete)
        self._btn_layout.addWidget(delete_btn)

        submit_btn = QPushButton("提交到开发")
        submit_btn.setObjectName("submitBtn")
        submit_btn.clicked.connect(self._on_submit)
        self._btn_layout.addWidget(submit_btn)

    def _setup_developing_ui(self):
        """设置开发实施修改状态的UI"""
        self._add_display_section("简要描述", self._issue.title)
        self._add_display_section("详细描述", self._issue.description, is_html=True)

        self._root_cause_editor = self._add_edit_section("问题原因", self._issue.root_cause, required=True)
        self._solution_editor = self._add_edit_section("问题修改", self._issue.solution, required=True)
        self._self_test_editor = self._add_edit_section("自测试", self._issue.self_test, required=True)

        # 模块选择
        module_group = QGroupBox("模块选择")
        module_layout = QHBoxLayout(module_group)
        module_label = QLabel("* 模块:")
        module_label.setStyleSheet("color: #E74C3C;")
        module_layout.addWidget(module_label)

        self._module_combo = QComboBox()
        self._module_combo.setMinimumWidth(200)
        self._load_modules()
        module_layout.addWidget(self._module_combo)
        module_layout.addStretch()

        self._content_layout.addWidget(module_group)
        self._content_layout.addStretch()

        # 按钮
        rollback_btn = QPushButton("回退到提交测试")
        rollback_btn.setObjectName("rollbackBtn")
        rollback_btn.clicked.connect(self._on_rollback)
        self._btn_layout.addWidget(rollback_btn)

        submit_btn = QPushButton("提交到归档")
        submit_btn.setObjectName("submitBtn")
        submit_btn.clicked.connect(self._on_submit)
        self._btn_layout.addWidget(submit_btn)

    def _setup_archived_ui(self):
        """设置归档状态的UI"""
        self._add_display_section("简要描述", self._issue.title)
        self._add_display_section("详细描述", self._issue.description, is_html=True)
        self._add_display_section("问题原因", self._issue.root_cause, is_html=True)
        self._add_display_section("问题修改", self._issue.solution, is_html=True)
        self._add_display_section("自测试", self._issue.self_test, is_html=True)

        if self._issue.module_name:
            self._add_display_section("所属模块", self._issue.module_name)

        self._archive_test_editor = self._add_edit_section("归档测试描述", self._issue.archive_test, required=True)

        self._content_layout.addStretch()

        # 按钮
        rollback_btn = QPushButton("回退到开发")
        rollback_btn.setObjectName("rollbackBtn")
        rollback_btn.clicked.connect(self._on_rollback)
        self._btn_layout.addWidget(rollback_btn)

        submit_btn = QPushButton("提交关闭")
        submit_btn.setObjectName("submitBtn")
        submit_btn.clicked.connect(self._on_submit)
        self._btn_layout.addWidget(submit_btn)

    def _setup_closed_ui(self):
        """设置关闭状态的UI"""
        self._add_display_section("简要描述", self._issue.title)
        self._add_display_section("详细描述", self._issue.description, is_html=True)
        self._add_display_section("问题原因", self._issue.root_cause, is_html=True)
        self._add_display_section("问题修改", self._issue.solution, is_html=True)
        self._add_display_section("自测试", self._issue.self_test, is_html=True)
        self._add_display_section("归档测试", self._issue.archive_test, is_html=True)

        if self._issue.module_name:
            self._add_display_section("所属模块", self._issue.module_name)

        self._content_layout.addStretch()

        # 按钮
        rollback_btn = QPushButton("回退到归档")
        rollback_btn.setObjectName("rollbackBtn")
        rollback_btn.clicked.connect(self._on_rollback)
        self._btn_layout.addWidget(rollback_btn)

    def _load_modules(self):
        """加载模块列表（当前项目的模块）"""
        if hasattr(self, '_module_combo'):
            self._module_combo.clear()
            self._module_combo.addItem("请选择模块", None)

            # 使用问题单所属项目的模块
            if self._issue and self._issue.project_id:
                modules = self._module_dao.get_by_project(self._issue.project_id)
                for module in modules:
                    self._module_combo.addItem(module.name, module.id)

                if self._issue.module_id:
                    index = self._module_combo.findData(self._issue.module_id)
                    if index >= 0:
                        self._module_combo.setCurrentIndex(index)

    def _add_display_section(self, title: str, content: str, is_html: bool = False):
        """添加显示区域"""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        if is_html and content:
            editor = RichTextEditor(issue_no=self._issue.issue_no, read_only=True)
            editor.set_html_content(content)
            # 自适应高度，最小120px
            editor.set_adaptive_height(min_height=120, max_height=800)
            layout.addWidget(editor)
        else:
            label = QLabel(content or "无")
            label.setWordWrap(True)
            label.setMinimumHeight(40)
            layout.addWidget(label)

        self._content_layout.addWidget(group)

    def _add_edit_section(self, title: str, content: str, required: bool = False) -> RichTextEditor:
        """添加编辑区域"""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        if required:
            group.setStyleSheet(group.styleSheet() + " QGroupBox::title { background-color: #E74C3C; }")

        editor = RichTextEditor(
            placeholder=f"请输入{title}...",
            issue_no=self._issue.issue_no
        )
        editor.set_min_height(720)  # 可编辑区域高度加大
        if content:
            editor.set_html_content(content)
        layout.addWidget(editor)

        self._content_layout.addWidget(group)
        return editor

    def _on_submit(self):
        """提交按钮点击"""
        if not self._issue:
            return

        status = self._issue.status

        valid, error_msg = self._validate_for_status(status)
        if not valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return

        try:
            self._collect_and_update()

            next_status = IssueStatus.get_next(status)
            if next_status:
                self._issue.status = IssueStatus(next_status)
                self._issue.status_changed_at = datetime.now()
                self._issue_dao.update(self._issue)

            self.issue_updated.emit(self._issue_id)
            QMessageBox.information(self, "操作成功", "问题单已更新！")

            # 刷新显示
            self.load_issue(self._issue_id)

        except Exception as e:
            QMessageBox.critical(self, "操作失败", str(e))

    def _on_rollback(self):
        """回退按钮点击"""
        if not self._issue:
            return

        reply = QMessageBox.question(
            self, "确认回退",
            "确定要将问题单回退到上一状态吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # 获取当前状态的整数值
            current_status = int(self._issue.status)
            prev_status = IssueStatus.get_prev(current_status)

            if prev_status is not None:
                self._issue.status = IssueStatus(prev_status)
                self._issue.status_changed_at = datetime.now()
                self._issue_dao.update(self._issue)

                self.issue_updated.emit(self._issue_id)
                QMessageBox.information(self, "回退成功", "问题单已回退！")

                # 刷新显示
                self.load_issue(self._issue_id)
            else:
                QMessageBox.warning(self, "回退失败", "当前状态无法回退")

        except Exception as e:
            QMessageBox.critical(self, "回退失败", str(e))

    def _on_delete(self):
        """销毁按钮点击"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要销毁这个问题单吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            if self._issue_dao.delete(self._issue_id):
                self.issue_deleted.emit(self._issue_id)
                QMessageBox.information(self, "删除成功", "问题单已删除！")
                self._on_close()
            else:
                QMessageBox.warning(self, "删除失败", "只有提交测试状态的问题单才能删除")

        except Exception as e:
            QMessageBox.critical(self, "删除失败", str(e))

    def _on_close(self):
        """关闭面板"""
        self.closed.emit()
        self.show_empty_state()

    def _validate_for_status(self, status: int) -> tuple[bool, str]:
        """验证当前状态的必填字段"""
        if status == IssueStatus.SUBMIT_TEST:
            # 提交测试状态验证简要描述和详细描述
            if hasattr(self, '_title_input'):
                if not self._title_input.text().strip():
                    return (False, "请填写简要描述")
                if not self._description_editor.get_plain_text().strip():
                    return (False, "请填写详细描述")
            return (True, "")

        elif status == IssueStatus.DEVELOPING:
            if hasattr(self, '_root_cause_editor'):
                if not self._root_cause_editor.get_plain_text().strip():
                    return (False, "请填写问题原因")
                if not self._solution_editor.get_plain_text().strip():
                    return (False, "请填写问题修改")
                if not self._self_test_editor.get_plain_text().strip():
                    return (False, "请填写自测试")
                if not self._module_combo.currentData():
                    return (False, "请选择模块")
            return (True, "")

        elif status == IssueStatus.ARCHIVED:
            if hasattr(self, '_archive_test_editor'):
                if not self._archive_test_editor.get_plain_text().strip():
                    return (False, "请填写归档测试描述")
            return (True, "")

        return (True, "")

    def _collect_and_update(self):
        """收集数据并更新问题单"""
        status = self._issue.status

        if status == IssueStatus.SUBMIT_TEST and hasattr(self, '_title_input'):
            self._issue.title = self._title_input.text().strip()
            self._issue.description = self._description_editor.get_html_content()
            self._issue.description = self._description_editor._image_manager.convert_to_relative_paths(self._issue.description)

        elif status == IssueStatus.DEVELOPING and hasattr(self, '_root_cause_editor'):
            self._issue.root_cause = self._root_cause_editor.get_html_content()
            self._issue.solution = self._solution_editor.get_html_content()
            self._issue.self_test = self._self_test_editor.get_html_content()
            self._issue.module_id = self._module_combo.currentData()

            self._issue.root_cause = self._root_cause_editor._image_manager.convert_to_relative_paths(self._issue.root_cause)
            self._issue.solution = self._root_cause_editor._image_manager.convert_to_relative_paths(self._issue.solution)
            self._issue.self_test = self._root_cause_editor._image_manager.convert_to_relative_paths(self._issue.self_test)

        elif status == IssueStatus.ARCHIVED and hasattr(self, '_archive_test_editor'):
            self._issue.archive_test = self._archive_test_editor.get_html_content()
            self._issue.archive_test = self._archive_test_editor._image_manager.convert_to_relative_paths(self._issue.archive_test)

        self._issue.updated_at = datetime.now()
        self._issue_dao.update(self._issue)