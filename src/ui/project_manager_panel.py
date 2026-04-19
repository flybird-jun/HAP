"""
项目管理面板模块

提供项目管理界面（嵌入主界面使用）
"""
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from ..data.database_manager import DatabaseManager
from ..data.project_dao import ProjectDAO
from ..models.project_model import Project


class ProjectManagerPanel(QWidget):
    """
    项目管理面板

    功能：
    - 展示项目列表（含模块数、问题单数）
    - 添加新项目
    - 编辑项目名称和描述
    - 删除项目（检查是否可删除）
    - 设置默认项目
    """

    # 信号定义
    projects_updated = Signal()  # 项目列表已更新信号
    closed = Signal()            # 关闭面板信号

    def __init__(self, parent=None):
        """初始化面板"""
        super().__init__(parent)

        # 初始化数据访问对象
        self._db = DatabaseManager.get_instance()
        self._project_dao = ProjectDAO(self._db)

        # 当前项目列表
        self._projects: List[Project] = []

        self.setup_ui()
        self.setup_style()
        self.load_projects()

    def setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题栏
        title_bar = QHBoxLayout()

        self._title_label = QLabel("项目管理")
        self._title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #F39C12;")
        title_bar.addWidget(self._title_label)

        title_bar.addStretch()

        self._close_btn = QPushButton("返回列表")
        self._close_btn.setObjectName("closePanelBtn")
        self._close_btn.clicked.connect(self._on_close)
        title_bar.addWidget(self._close_btn)

        layout.addLayout(title_bar)

        # 添加项目区域
        add_group = QWidget()
        add_group.setObjectName("addGroup")
        add_layout = QVBoxLayout(add_group)
        add_layout.setContentsMargins(10, 10, 10, 10)
        add_layout.setSpacing(10)

        # 名称输入行
        name_layout = QHBoxLayout()
        name_label = QLabel("* 项目名称:")
        name_label.setStyleSheet("color: #E74C3C;")
        name_layout.addWidget(name_label)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("请输入项目名称...")
        self._name_input.setMaxLength(50)
        name_layout.addWidget(self._name_input, stretch=1)
        add_layout.addLayout(name_layout)

        # 描述输入行
        desc_layout = QHBoxLayout()
        desc_label = QLabel("  项目描述:")
        desc_layout.addWidget(desc_label)

        self._desc_input = QLineEdit()
        self._desc_input.setPlaceholderText("请输入项目描述（可选）...")
        self._desc_input.setMaxLength(200)
        desc_layout.addWidget(self._desc_input, stretch=1)
        add_layout.addLayout(desc_layout)

        # 添加按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._add_btn = QPushButton("添加项目")
        self._add_btn.setObjectName("addBtn")
        self._add_btn.clicked.connect(self.on_add_project)
        btn_row.addWidget(self._add_btn)
        add_layout.addLayout(btn_row)

        layout.addWidget(add_group)

        # 项目列表表格
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["序号", "项目名称", "描述", "模块数/问题数", "操作"])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(60)

        # 设置列宽
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(1, 150)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 150)

        layout.addWidget(self._table, stretch=1)

        # 统计信息
        self._statistics_label = QLabel("统计: 共 0 个项目")
        self._statistics_label.setStyleSheet("color: #888888; font-size: 14px;")
        layout.addWidget(self._statistics_label)

    def setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            ProjectManagerPanel {
                background-color: #1E1E2E;
            }

            QWidget#addGroup {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
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
                padding: 10px;
                color: #FFFFFF;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 2px solid #3498DB;
            }

            QPushButton {
                background-color: #3E3E4E;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                color: #FFFFFF;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #4E4E5E;
            }

            QPushButton#addBtn {
                background-color: #27AE60;
                font-weight: bold;
            }

            QPushButton#addBtn:hover {
                background-color: #2ECC71;
            }

            QPushButton#editBtn {
                background-color: #3498DB;
                padding: 8px 16px;
                font-size: 14px;
            }

            QPushButton#editBtn:hover {
                background-color: #2980B9;
            }

            QPushButton#deleteBtn {
                background-color: #E74C3C;
                padding: 8px 16px;
                font-size: 14px;
            }

            QPushButton#deleteBtn:hover {
                background-color: #C0392B;
            }

            QPushButton#closePanelBtn {
                background-color: #3498DB;
            }

            QPushButton#closePanelBtn:hover {
                background-color: #2980B9;
            }

            QTableWidget {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                gridline-color: transparent;
                color: #FFFFFF;
                font-size: 14px;
            }

            QTableWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid #3E3E4E;
                background-color: #2E2E3E;
            }

            QTableWidget::item:selected {
                background-color: #3498DB;
                color: #FFFFFF;
            }

            QTableWidget::item:hover {
                background-color: #3E3E4E;
            }

            QHeaderView::section {
                background-color: #1E1E2E;
                border: none;
                border-bottom: 2px solid #3498DB;
                padding: 12px 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def _on_close(self):
        """关闭面板"""
        self.closed.emit()

    def load_projects(self):
        """加载项目列表"""
        self._projects = self._project_dao.get_all_with_stats()
        self.refresh_table()
        self.update_statistics()

    def refresh_table(self):
        """刷新表格数据"""
        self._table.setRowCount(len(self._projects))

        for row, project in enumerate(self._projects):
            # 序号
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, index_item)

            # 项目名称
            name_item = QTableWidgetItem(project.name)
            self._table.setItem(row, 1, name_item)

            # 描述
            desc_item = QTableWidgetItem(project.description or "--")
            self._table.setItem(row, 2, desc_item)

            # 模块数/问题数
            stats_item = QTableWidgetItem(f"{project.module_count}/{project.issue_count}")
            stats_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, stats_item)

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            btn_layout.setSpacing(4)

            # 编辑按钮
            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("editBtn")
            edit_btn.clicked.connect(lambda checked, p=project: self.on_edit_project(p))
            btn_layout.addWidget(edit_btn)

            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setObjectName("deleteBtn")
            delete_btn.clicked.connect(lambda checked, p=project: self.on_delete_project(p))
            btn_layout.addWidget(delete_btn)

            self._table.setCellWidget(row, 4, btn_widget)

    def update_statistics(self):
        """更新统计信息"""
        total_projects = len(self._projects)
        total_modules = sum(p.module_count for p in self._projects)
        total_issues = sum(p.issue_count for p in self._projects)
        self._statistics_label.setText(
            f"统计: 共 {total_projects} 个项目，{total_modules} 个模块，{total_issues} 个问题单"
        )

    def on_add_project(self):
        """添加项目"""
        name = self._name_input.text().strip()
        description = self._desc_input.text().strip()

        # 验证名称
        valid, error_msg = self.validate_project_name(name)
        if not valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return

        try:
            self._project_dao.create(name, description)
            self._name_input.clear()
            self._desc_input.clear()
            self.load_projects()
            self.projects_updated.emit()
            QMessageBox.information(self, "添加成功", f"项目 '{name}' 已添加！")

        except Exception as e:
            QMessageBox.warning(self, "添加失败", str(e))

    def on_edit_project(self, project: Project):
        """编辑项目"""
        from PySide6.QtWidgets import QInputDialog

        # 编辑名称
        new_name, ok = QInputDialog.getText(
            self, "编辑项目", "请输入新的项目名称:",
            QLineEdit.Normal, project.name
        )

        if not ok:
            return

        new_name = new_name.strip()

        # 验证名称
        valid, error_msg = self.validate_project_name(new_name, exclude_id=project.id)
        if not valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return

        # 编辑描述
        new_desc, ok = QInputDialog.getText(
            self, "编辑项目", "请输入新的项目描述:",
            QLineEdit.Normal, project.description or ""
        )

        if not ok:
            return

        try:
            self._project_dao.update(project.id, new_name, new_desc.strip())
            self.load_projects()
            self.projects_updated.emit()
            QMessageBox.information(self, "编辑成功", f"项目已更新！")

        except Exception as e:
            QMessageBox.warning(self, "编辑失败", str(e))

    def on_delete_project(self, project: Project):
        """删除项目"""
        # 检查是否可删除
        can_delete, reason = self._project_dao.can_delete(project.id)
        if not can_delete:
            QMessageBox.warning(self, "无法删除", f"项目 '{project.name}' 无法删除：{reason}")
            return

        # 确认删除
        msg = f"确定要删除项目 '{project.name}' 吗？\n该项目有 {project.module_count} 个模块，删除后模块也将被删除。"
        reply = QMessageBox.question(
            self, "确认删除", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self._project_dao.delete(project.id)
            self.load_projects()
            self.projects_updated.emit()
            QMessageBox.information(self, "删除成功", f"项目 '{project.name}' 已删除！")

        except Exception as e:
            QMessageBox.warning(self, "删除失败", str(e))

    def validate_project_name(self, name: str, exclude_id: int = None) -> tuple[bool, str]:
        """验证项目名称"""
        if not name:
            return (False, "项目名称不能为空")

        if len(name) > 50:
            return (False, "项目名称不能超过50个字符")

        if self._project_dao.is_name_exists(name, exclude_id):
            return (False, f"项目名称 '{name}' 已存在")

        return (True, "")