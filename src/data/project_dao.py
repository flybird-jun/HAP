"""
项目数据访问模块

负责项目的增删改查操作
"""
from typing import List, Optional
from datetime import datetime

from .database_manager import DatabaseManager
from ..models.project_model import Project


class ProjectDAO:
    """
    项目数据访问对象

    功能：
    - 项目的CRUD操作
    - 默认项目管理
    - 名称唯一性验证
    - 项目统计信息
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化DAO

        Args:
            db_manager: 数据库管理器实例，如果为None则自动获取
        """
        self._db = db_manager or DatabaseManager.get_instance()

    def create(self, name: str, description: str = "", is_default: bool = False) -> int:
        """
        创建项目

        Args:
            name: 项目名称
            description: 项目描述
            is_default: 是否为默认项目

        Returns:
            新创建的项目ID

        Raises:
            ValueError: 名称为空
            sqlite3.IntegrityError: 名称已存在
        """
        if not name or not name.strip():
            raise ValueError("项目名称不能为空")

        name = name.strip()

        if self.is_name_exists(name):
            raise ValueError(f"项目名称 '{name}' 已存在")

        now = self._db.get_timestamp()
        sql = """
            INSERT INTO project (name, description, is_default, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = self._db.execute(sql, (name, description, 1 if is_default else 0, now, now))
        self._db.commit()
        return cursor.lastrowid

    def get_by_id(self, project_id: int) -> Optional[Project]:
        """
        根据ID获取项目

        Args:
            project_id: 项目ID

        Returns:
            项目模型，不存在返回None
        """
        sql = "SELECT * FROM project WHERE id = ?"
        data = self._db.fetchone(sql, (project_id,))
        if data:
            return Project.from_dict(data)
        return None

    def get_by_name(self, name: str) -> Optional[Project]:
        """
        根据名称获取项目

        Args:
            name: 项目名称

        Returns:
            项目模型，不存在返回None
        """
        sql = "SELECT * FROM project WHERE name = ?"
        data = self._db.fetchone(sql, (name,))
        if data:
            return Project.from_dict(data)
        return None

    def get_all(self) -> List[Project]:
        """
        获取所有项目

        Returns:
            项目列表，按创建时间排序
        """
        sql = "SELECT * FROM project ORDER BY created_at ASC"
        data_list = self._db.fetchall(sql)
        return [Project.from_dict(data) for data in data_list]

    def get_default_project(self) -> Optional[Project]:
        """
        获取默认项目

        Returns:
            默认项目，不存在返回None
        """
        sql = "SELECT * FROM project WHERE is_default = 1"
        data = self._db.fetchone(sql)
        if data:
            return Project.from_dict(data)
        return None

    def get_all_with_stats(self) -> List[Project]:
        """
        获取所有项目及统计信息

        Returns:
            项目列表，包含模块数和问题单数
        """
        sql = """
            SELECT
                p.id, p.name, p.description, p.is_default, p.created_at, p.updated_at,
                COUNT(DISTINCT m.id) as module_count,
                COUNT(DISTINCT i.id) as issue_count
            FROM project p
            LEFT JOIN module m ON p.id = m.project_id
            LEFT JOIN issue i ON p.id = i.project_id
            GROUP BY p.id
            ORDER BY p.created_at ASC
        """
        data_list = self._db.fetchall(sql)
        return [Project.from_dict(data) for data in data_list]

    def update(self, project_id: int, name: str, description: str = "") -> bool:
        """
        更新项目

        Args:
            project_id: 项目ID
            name: 新的项目名称
            description: 新的项目描述

        Returns:
            更新是否成功

        Raises:
            ValueError: 名称为空或已存在
        """
        if not name or not name.strip():
            raise ValueError("项目名称不能为空")

        name = name.strip()

        if self.is_name_exists(name, exclude_id=project_id):
            raise ValueError(f"项目名称 '{name}' 已存在")

        now = self._db.get_timestamp()
        sql = "UPDATE project SET name = ?, description = ?, updated_at = ? WHERE id = ?"
        self._db.execute(sql, (name, description, now, project_id))
        self._db.commit()
        return True

    def delete(self, project_id: int) -> bool:
        """
        删除项目

        Args:
            project_id: 项目ID

        Returns:
            删除是否成功

        Raises:
            ValueError: 项目不可删除（默认项目或有问题单）
        """
        project = self.get_by_id(project_id)
        if project is None:
            return False

        if project.is_default:
            raise ValueError("默认项目不能删除")

        issue_count = self.count_issues(project_id)
        if issue_count > 0:
            raise ValueError(f"该项目有 {issue_count} 个问题单，无法删除")

        sql = "DELETE FROM project WHERE id = ?"
        self._db.execute(sql, (project_id,))
        self._db.commit()
        return True

    def can_delete(self, project_id: int) -> tuple[bool, str]:
        """
        检查项目是否可删除

        Args:
            project_id: 项目ID

        Returns:
            (是否可删除, 原因说明)
        """
        project = self.get_by_id(project_id)
        if project is None:
            return (False, "项目不存在")

        if project.is_default:
            return (False, "默认项目不能删除")

        issue_count = self.count_issues(project_id)
        if issue_count > 0:
            return (False, f"该项目有 {issue_count} 个问题单")

        return (True, "")

    def is_name_exists(self, name: str, exclude_id: int = None) -> bool:
        """
        检查项目名是否已存在

        Args:
            name: 要检查的名称
            exclude_id: 排除的项目ID（用于更新时排除自身）

        Returns:
            名称是否存在
        """
        if exclude_id:
            sql = "SELECT COUNT(*) as count FROM project WHERE name = ? AND id != ?"
            data = self._db.fetchone(sql, (name.strip(), exclude_id))
        else:
            sql = "SELECT COUNT(*) as count FROM project WHERE name = ?"
            data = self._db.fetchone(sql, (name.strip(),))

        return data['count'] > 0 if data else False

    def set_as_default(self, project_id: int) -> bool:
        """
        设置指定项目为默认项目

        Args:
            project_id: 项目ID

        Returns:
            设置是否成功
        """
        project = self.get_by_id(project_id)
        if project is None:
            return False

        now = self._db.get_timestamp()

        # 先取消当前默认项目
        self._db.execute("UPDATE project SET is_default = 0 WHERE is_default = 1")

        # 设置新默认项目
        self._db.execute(
            "UPDATE project SET is_default = 1, updated_at = ? WHERE id = ?",
            (now, project_id)
        )
        self._db.commit()
        return True

    def count_issues(self, project_id: int) -> int:
        """
        统计项目关联的问题单数量

        Args:
            project_id: 项目ID

        Returns:
            关联的问题单数量
        """
        sql = "SELECT COUNT(*) as count FROM issue WHERE project_id = ?"
        data = self._db.fetchone(sql, (project_id,))
        return data['count'] if data else 0

    def count_modules(self, project_id: int) -> int:
        """
        统计项目关联的模块数量

        Args:
            project_id: 项目ID

        Returns:
            关联的模块数量
        """
        sql = "SELECT COUNT(*) as count FROM module WHERE project_id = ?"
        data = self._db.fetchone(sql, (project_id,))
        return data['count'] if data else 0

    def count_all(self) -> int:
        """
        统计项目总数

        Returns:
            项目总数
        """
        sql = "SELECT COUNT(*) as count FROM project"
        data = self._db.fetchone(sql)
        return data['count'] if data else 0