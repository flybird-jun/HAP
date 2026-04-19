"""
数据库管理模块

负责SQLite数据库的连接管理、表结构初始化
"""
import sqlite3
import os
import sys
from typing import Optional, List, Tuple
from datetime import datetime


def get_data_path(relative_path):
    """获取数据文件的绝对路径（持久化目录）"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后，数据文件放在 exe 所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


class DatabaseManager:
    """
    数据库管理器

    使用单例模式，确保全局只有一个数据库连接实例

    功能：
    - 管理SQLite数据库连接
    - 初始化数据库表结构
    - 提供数据库操作的基础方法
    """

    _instance: Optional['DatabaseManager'] = None
    _initialized: bool = False

    def __new__(cls, db_path: str = None):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为 data/issue_tracking.db
        """
        # 避免重复初始化
        if DatabaseManager._initialized:
            return

        if db_path is None:
            # 默认数据库路径（支持打包后运行）
            db_path = get_data_path('data/issue_tracking.db')

        self._db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化连接
        self._init_connection()
        self._init_tables()

        DatabaseManager._initialized = True

    def _init_connection(self):
        """初始化数据库连接"""
        self._connection = sqlite3.connect(
            self._db_path,
            check_same_thread=False,  # 允许多线程访问
            isolation_level=None      # 手动控制事务
        )

        # 启用外键约束
        self._connection.execute("PRAGMA foreign_keys = ON")

        # 设置行工厂，返回字典形式的结果
        self._connection.row_factory = sqlite3.Row

    def _init_tables(self):
        """初始化数据库表结构"""
        # 检查是否需要迁移（是否已有project表）
        need_migration = self._check_need_migration()

        # 项目表
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 创建项目索引
        self._connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_project_name ON project(name)")

        # 确保存在默认项目
        self._ensure_default_project()

        if need_migration:
            # 执行数据迁移
            self._migrate_to_project_support()

        # 模块表（带project_id）
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS module (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                project_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
                UNIQUE(name, project_id)
            )
        """)

        # 问题单表（带project_id）
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS issue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_no TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                module_id INTEGER,
                project_id INTEGER NOT NULL,
                status INTEGER NOT NULL DEFAULT 0,
                root_cause TEXT,
                solution TEXT,
                self_test TEXT,
                archive_test TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status_changed_at TEXT NOT NULL,
                FOREIGN KEY (module_id) REFERENCES module(id) ON DELETE SET NULL,
                FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE RESTRICT
            )
        """)

        # 图片表
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS image (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (issue_id) REFERENCES issue(id) ON DELETE CASCADE
            )
        """)

        # 创建索引
        self._connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_issue_no ON issue(issue_no)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_issue_status ON issue(status)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_issue_created ON issue(created_at)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_issue_project ON issue(project_id)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_module_project ON module(project_id)")
        self._connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_module_name_project ON module(name, project_id)")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_image_issue ON image(issue_id)")

        self._connection.commit()

    def _check_need_migration(self) -> bool:
        """检查是否需要迁移（旧版本数据库无project表）"""
        cursor = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='project'"
        )
        if cursor.fetchone() is None:
            # project表不存在，需要迁移
            return True

        # 检查issue表是否有project_id字段
        cursor = self._connection.execute("PRAGMA table_info(issue)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'project_id' not in columns:
            return True

        return False

    def _ensure_default_project(self):
        """确保存在默认项目"""
        cursor = self._connection.execute(
            "SELECT id FROM project WHERE is_default = 1"
        )
        if cursor.fetchone() is None:
            # 创建默认项目
            now = self.get_timestamp()
            self._connection.execute("""
                INSERT INTO project (name, description, is_default, created_at, updated_at)
                VALUES ('默认项目', '系统默认项目', 1, ?, ?)
            """, (now, now))
            self._connection.commit()

    def _migrate_to_project_support(self):
        """迁移旧数据到支持项目的结构"""
        # 获取默认项目ID
        cursor = self._connection.execute(
            "SELECT id FROM project WHERE is_default = 1"
        )
        result = cursor.fetchone()
        default_project_id = result[0] if result else 1

        # 检查module表是否需要重建
        cursor = self._connection.execute("PRAGMA table_info(module)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'project_id' not in columns:
            # 重建module表
            self._connection.execute("""
                CREATE TABLE module_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    project_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE,
                    UNIQUE(name, project_id)
                )
            """)
            # 迁移现有模块到默认项目
            self._connection.execute("""
                INSERT INTO module_new (id, name, project_id, created_at)
                SELECT id, name, ?, created_at FROM module
            """, (default_project_id,))
            # 删除旧表
            self._connection.execute("DROP TABLE module")
            self._connection.execute("ALTER TABLE module_new RENAME TO module")

        # 检查issue表是否需要添加project_id
        cursor = self._connection.execute("PRAGMA table_info(issue)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'project_id' not in columns:
            # 添加project_id字段（SQLite不支持NOT NULL约束，需要重建）
            self._connection.execute("""
                CREATE TABLE issue_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_no TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    description TEXT,
                    module_id INTEGER,
                    project_id INTEGER NOT NULL,
                    status INTEGER NOT NULL DEFAULT 0,
                    root_cause TEXT,
                    solution TEXT,
                    self_test TEXT,
                    archive_test TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status_changed_at TEXT NOT NULL,
                    FOREIGN KEY (module_id) REFERENCES module(id) ON DELETE SET NULL,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE RESTRICT
                )
            """)
            # 迁移现有问题单到默认项目
            self._connection.execute("""
                INSERT INTO issue_new
                SELECT id, issue_no, title, description, module_id, ?, status,
                       root_cause, solution, self_test, archive_test,
                       created_at, updated_at, status_changed_at
                FROM issue
            """, (default_project_id,))
            # 删除旧表
            self._connection.execute("DROP TABLE issue")
            self._connection.execute("ALTER TABLE issue_new RENAME TO issue")

        self._connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return self._connection

    @property
    def db_path(self) -> str:
        """获取数据库路径"""
        return self._db_path

    def execute(self, sql: str, params: Tuple = None) -> sqlite3.Cursor:
        """
        执行SQL语句

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            Cursor对象
        """
        if params:
            return self._connection.execute(sql, params)
        return self._connection.execute(sql)

    def executemany(self, sql: str, params_list: List[Tuple]) -> sqlite3.Cursor:
        """
        批量执行SQL语句

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            Cursor对象
        """
        return self._connection.executemany(sql, params_list)

    def fetchone(self, sql: str, params: Tuple = None) -> Optional[dict]:
        """
        查询单条记录

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            字典形式的单条记录，或 None
        """
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def fetchall(self, sql: str, params: Tuple = None) -> List[dict]:
        """
        查询多条记录

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            字典形式的记录列表
        """
        cursor = self.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def begin_transaction(self):
        """开始事务"""
        self._connection.execute("BEGIN TRANSACTION")

    def commit(self):
        """提交事务"""
        self._connection.commit()

    def rollback(self):
        """回滚事务"""
        self._connection.rollback()

    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
            DatabaseManager._instance = None
            DatabaseManager._initialized = False

    def reset(self):
        """
        重置数据库（清空所有数据）

        注意：这是一个危险操作，仅在测试或初始化时使用
        """
        self._connection.execute("DELETE FROM image")
        self._connection.execute("DELETE FROM issue")
        self._connection.execute("DELETE FROM module")
        self._connection.commit()

    def get_timestamp(self) -> str:
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def get_instance(cls, db_path: str = None) -> 'DatabaseManager':
        """
        获取单例实例

        Args:
            db_path: 数据库路径

        Returns:
            DatabaseManager实例
        """
        return cls(db_path)