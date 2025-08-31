# partyapp/cli.py
import typer
from partyapp.db.base import Base, engine
from partyapp.db.models import *  # モデルを読み込む
from sqlalchemy import text, inspect

cli = typer.Typer()

@cli.command()
def init_db():
    """partyappdbにDBスキーマを作成（初回のみ使用）"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema created")

@cli.command()
def drop_db():
    """partyappdbのDBスキーマを全削除（開発用）"""
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

@cli.command()
def list_models():
    """partyappdbのモデル一覧を表示"""
    if not Base.metadata.tables:
        print("⚠️ モデルが読み込まれていません。")
        return

    print("📋 定義済みモデル一覧:")
    for name, table in Base.metadata.tables.items():
        print(f"- {name}")

# show_model_schemaコマンドで利用するローカル関数
def _iter_models():
    # Baseにぶら下がっている全モデルクラスを列挙
    for mapper in Base.registry.mappers:
        yield mapper.class_

def _get_model_class(model_name: str):
    for cls in _iter_models():
        if cls.__name__ == model_name:
            return cls
    return None

@cli.command()
def show_model_schema(model_name: str):
    """モデル名で指定したモデルのスキーマを表示"""
    cls = _get_model_class(model_name)
    if cls is None:
        print(f"⚠️ モデル '{model_name}' は見つかりません。")
        return

    mapper = inspect(cls)  # または cls.__table__ でもOK
    selectable = mapper.persist_selectable
    print(f"\n📦 Model: {cls.__name__}  /  Table: {getattr(selectable, 'name', str(type(selectable)))}\n")
    
    print("🧱 Columns:")
    for c in selectable.columns:  # Table でも Join でも .columns は使えます
        pk = " PK" if getattr(c, "primary_key", False) else ""
        nn = " NOT NULL" if getattr(c, "nullable", True) is False else ""
        print(f"- {c.name}: {c.type}{nn}{pk}")
    print()  

if __name__ == "__main__":
    cli()