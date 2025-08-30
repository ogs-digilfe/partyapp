# partyapp/cli.py
import typer
from partyapp.db.base import Base, engine
from partyapp.db.models import *  # モデルを読み込む
from sqlalchemy import create_engine, text
from partyapp.config import DATABASE_URL

cli = typer.Typer()

@cli.command()
def init_db():
    """partyappdbにDBスキーマを作成（初回のみ使用）"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema created")

@cli.command()
def drop_db():
    """partyappdbのDBスキーマを削除（開発用）"""
    Base.metadata.drop_all(bind=engine)
    print("🗑️ Database schema dropped")

@cli.command()
def connect_db():
    """partyappdbへの接続可否テスト"""
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar_one()
            print("✅ 接続成功！MariaDBバージョン:", version)
    except Exception as e:
        print("❌ 接続失敗:", e)

if __name__ == "__main__":
    cli()