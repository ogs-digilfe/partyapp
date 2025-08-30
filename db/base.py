from __future__ import annotations
from typing import Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from partyapp.config import DATABASE_URL

# Alembic と相性の良い命名規約（重要）
# 各制約における制約名の命名規則を厳密化することで、Alembicによるdb migration(スキーマ変更)を容易にする
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s__%(column_0_name)s",
    "ck": "ck_%(table_name)s__%(constraint_name)s",
    "fk": "fk_%(table_name)s__%(column_0_name)s__%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata_obj = MetaData(naming_convention=NAMING_CONVENTION)


# SQL Alchemyのデータベーステーブルオブジェクトの親クラス
# テーブルを定義したクラスを作成する際、Baseクラスを継承して作成する。
class Base(DeclarativeBase):
    metadata = metadata_obj


# ---- MySQL 用エンジン設定 ----
# engine: 物理的なコネクションの入口
# DB接続プールの管理者（低レベルのハンドラ）
# RDBMSとの物理的な接続やコネクションプーリングを直接扱う。
# engine.connect() で生の接続を取って直接 SQL を流すこともできる。
# DATABASE_URL の例:
# mysql+pymysql://user:password@localhost:3306/dbname
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,         # 切断検知を有効化
    pool_recycle=3600,          # MySQL の wait_timeout 対策（1時間ごとに再接続）
    echo=False,                 # True にするとSQLログ出力
    future=True,                # SQLAlchemy 2.0 スタイル
)

# SessionLocal: ORMを使ってDBと対話する窓口
# ORM用の接続ハンドラ（高レベルの会話役）
# engine を内部で利用しつつ、トランザクション管理や ORM モデル操作をまとめてくれる。
# sessionmaker で作った「セッション生成工場」で、呼び出すたびに新しい Session を生成する。
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# get_session: セッションのライフサイクルを安全に扱うための仕組み
# SessionLocal() を生成して返すジェネレータヘルパー
# 処理が終わったら finally: db.close() を必ず実行するようになっている。
# FastAPI のように「依存性注入」に組み込むと、リクエストごとに自動的にセッションを開閉してくれる。
def get_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()