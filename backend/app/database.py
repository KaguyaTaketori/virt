from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///./streams.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 等锁最多 30 秒再报错
    },
    poolclass=StaticPool,
    echo=False
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    """每次新连接时设置 SQLite 性能参数。"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # 读写不互斥
    cursor.execute("PRAGMA synchronous=NORMAL")  # 性能与安全平衡
    cursor.execute("PRAGMA cache_size=10000")  # 约 40MB 内存缓存
    cursor.execute("PRAGMA temp_store=MEMORY")  # 临时表放内存
    cursor.execute("PRAGMA mmap_size=134217728")  # 128MB mmap
    cursor.execute("PRAGMA encoding='UTF-8'")  # UTF-8编码
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
