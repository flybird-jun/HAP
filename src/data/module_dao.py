"""
模块数据访问模块

负责模块的增删改查操作
"""
from typing import List, Optional
from datetime import datetime

from .database_manager import DatabaseManager
from ..models.module_model import Module


class ModuleDAO:
    """
    模块数据访问对象

    功能：
    - 模块的CRUD操作
    - 名称唯一性验证
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化DAO

        Args:
            db_manager: 数据库管理器实例，如果为None则自动获取
        """
        self._db = db_manager or DatabaseManager.get_instance()

    def create(self, name: str, project_id: int) -> int:
        """
        创建模块

        Args:
            name: 模块名称
            project_id: 所属项目ID

        Returns:
            新创建的模块ID

        Raises:
            ValueError: 名称为空或项目ID无效
            sqlite3.IntegrityError: 项目内名称已存在
        """
        if not name or not name.strip():
            raise ValueError("模块名称不能为空")

        if project_id is None:
            raise ValueError("必须指定所属项目")

        name = name.strip()

        # 检查项目内名称是否已存在
        if self.is_name_exists(name, project_id):
            raise ValueError(f"该项目内模块名称 '{name}' 已存在")

        now = self._db.get_timestamp()
        sql = "INSERT INTO module (name, project_id, created_at) VALUES (?, ?, ?)"
        cursor = self._db.execute(sql, (name, project_id, now))
        self._db.commit()
        return cursor.lastrowid

    def get_by_id(self, module_id: int) -> Optional[Module]:
        """
        根据ID获取模块

        Args:
            module_id: 模块ID

        Returns:
            模块模型，不存在返回None
        """
        sql = """
            SELECT m.*, p.name as project_name
            FROM module m
            LEFT JOIN project p ON m.project_id = p.id
            WHERE m.id = ?
        """
        data = self._db.fetchone(sql, (module_id,))
        if data:
            return Module.from_dict(data)
        return None

    def get_by_name(self, name: str, project_id: int) -> Optional[Module]:
        """
        根据名称和项目获取模块

        Args:
            name: 模块名称
            project_id: 项目ID

        Returns:
            模块模型，不存在返回None
        """
        sql = """
            SELECT m.*, p.name as project_name
            FROM module m
            LEFT JOIN project p ON m.project_id = p.id
            WHERE m.name = ? AND m.project_id = ?
        """
        data = self._db.fetchone(sql, (name, project_id))
        if data:
            return Module.from_dict(data)
        return None

    def get_by_project(self, project_id: int) -> List[Module]:
        """
        获取指定项目的模块列表

        Args:
            project_id: 项目ID

        Returns:
            该项目的模块列表
        """
        sql = """
            SELECT m.*, p.name as project_name
            FROM module m
            LEFT JOIN project p ON m.project_id = p.id
            WHERE m.project_id = ?
            ORDER BY m.created_at ASC
        """
        data_list = self._db.fetchall(sql, (project_id,))
        return [Module.from_dict(data) for data in data_list]

    def get_all(self) -> List[Module]:
        """
        获取所有模块

        Returns:
            模块列表，按创建时间排序
        """
        sql = """
            SELECT m.*, p.name as project_name
            FROM module m
            LEFT JOIN project p ON m.project_id = p.id
            ORDER BY m.created_at ASC
        """
        data_list = self._db.fetchall(sql)
        return [Module.from_dict(data) for data in data_list]

    def update(self, module_id: int, name: str, project_id: int = None) -> bool:
        """
        更新模块

        Args:
            module_id: 模块ID
            name: 新的模块名称
            project_id: 新的项目ID（可选，不传则不更新项目）

        Returns:
            更新是否成功

        Raises:
            ValueError: 名称为空或项目内已存在
        """
        # 获取现有模块
        module = self.get_by_id(module_id)
        if module is None:
            return False

        # 验证名称
        if not name or not name.strip():
            raise ValueError("模块名称不能为空")

        name = name.strip()

        # 确定目标项目ID
        target_project_id = project_id if project_id is not None else module.project_id

        # 检查项目内名称是否已存在（排除当前模块）
        if self.is_name_exists(name, target_project_id, exclude_id=module_id):
            raise ValueError(f"该项目内模块名称 '{name}' 已存在")

        if project_id is not None:
            sql = "UPDATE module SET name = ?, project_id = ? WHERE id = ?"
            self._db.execute(sql, (name, project_id, module_id))
        else:
            sql = "UPDATE module SET name = ? WHERE id = ?"
            self._db.execute(sql, (name, module_id))
        self._db.commit()
        return True

    def delete(self, module_id: int) -> bool:
        """
        删除模块

        Args:
            module_id: 模块ID

        Returns:
            删除是否成功
        """
        # 检查模块是否存在
        module = self.get_by_id(module_id)
        if module is None:
            return False

        sql = "DELETE FROM module WHERE id = ?"
        self._db.execute(sql, (module_id,))
        self._db.commit()
        return True

    def is_name_exists(self, name: str, project_id: int, exclude_id: int = None) -> bool:
        """
        检查模块名是否已存在（项目内）

        Args:
            name: 要检查的名称
            project_id: 项目ID
            exclude_id: 排除的模块ID（用于更新时排除自身）

        Returns:
            名称是否存在
        """
        if exclude_id:
            sql = "SELECT COUNT(*) as count FROM module WHERE name = ? AND project_id = ? AND id != ?"
            data = self._db.fetchone(sql, (name.strip(), project_id, exclude_id))
        else:
            sql = "SELECT COUNT(*) as count FROM module WHERE name = ? AND project_id = ?"
            data = self._db.fetchone(sql, (name.strip(), project_id))

        return data['count'] > 0 if data else False

    def count_issues(self, module_id: int) -> int:
        """
        统计模块关联的问题单数量

        Args:
            module_id: 模块ID

        Returns:
            关联的问题单数量
        """
        sql = "SELECT COUNT(*) as count FROM issue WHERE module_id = ?"
        data = self._db.fetchone(sql, (module_id,))
        return data['count'] if data else 0

    def get_all_with_issue_count(self) -> List[Module]:
        """
        获取所有模块及其关联的问题单数量

        Returns:
            模块列表，包含问题单数量和项目名称
        """
        sql = """
            SELECT
                m.id, m.name, m.project_id, m.created_at,
                p.name as project_name,
                COUNT(i.id) as issue_count
            FROM module m
            LEFT JOIN project p ON m.project_id = p.id
            LEFT JOIN issue i ON m.id = i.module_id
            GROUP BY m.id
            ORDER BY m.created_at ASC
        """
        data_list = self._db.fetchall(sql)
        return [Module.from_dict(data) for data in data_list]

    def get_by_project_with_issue_count(self, project_id: int) -> List[Module]:
        """
        获取指定项目的模块及其关联的问题单数量

        Args:
            project_id: 项目ID

        Returns:
            模块列表，包含问题单数量
        """
        sql = """
            SELECT
                m.id, m.name, m.project_id, m.created_at,
                p.name as project_name,
                COUNT(i.id) as issue_count
            FROM module m
            LEFT JOIN project p ON m.project_id = p.id
            LEFT JOIN issue i ON m.id = i.module_id
            WHERE m.project_id = ?
            GROUP BY m.id
            ORDER BY m.created_at ASC
        """
        data_list = self._db.fetchall(sql, (project_id,))
        return [Module.from_dict(data) for data in data_list]

    def count_all(self) -> int:
        """
        统计模块总数

        Returns:
            模块总数
        """
        sql = "SELECT COUNT(*) as count FROM module"
        data = self._db.fetchone(sql)
        return data['count'] if data else 0