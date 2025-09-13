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
    """partyappdbのモデル一覧を表示（テーブル名とモデル名）"""
    if not Base.metadata.tables:
        print("⚠️ モデルが読み込まれていません。")
        return

    print("📋 定義済みモデル一覧(モデル名/テーブル名):")
    # Base を継承したクラスをすべて取得
    for cls in Base.__subclasses__():
        model_name = cls.__name__
        table_name = getattr(cls, "__tablename__", "(not set)")
        print(f"- {model_name}/{table_name}")

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


#################################################################
# 以下は、seedツール
#################################################################
#
# imoprt objects for seed tool
#
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, date, timezone
import random

import typer
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from partyapp.db.base import SessionLocal
from partyapp.db.models import Party, Category, Law, PartyLawRole
from partyapp.db.models.enums import PartyRole

# ==============================================================
# ID 生成ユーティリティ（CHAR(18)）
# ==============================================================

# Crockford Base32（0-9 A-Z ただし I L O U を除く）
_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def _to_base32(n: int) -> str:
    if n == 0:
        return "0"
    s = []
    while n > 0:
        n, r = divmod(n, 32)
        s.append(_B32[r])
    return "".join(reversed(s))

def make_char18_id() -> str:
    """
    時刻(ミリ秒)をBase32化した先頭に、残りをランダムBase32でパディングして18文字。
    既存行に対しては ON DUPLICATE KEY UPDATE で id=id とし、id は変更しない。
    """
    millis = int(datetime.now(timezone.utc).timestamp() * 1000)
    head = _to_base32(millis)
    if len(head) > 18:
        head = head[:18]
    pad = "".join(random.choice(_B32) for _ in range(18 - len(head)))
    return (head + pad)[:18]

# ==============================================================
# seed utility functions
# ==============================================================

def read_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        typer.echo(f"⚠ {path} が見つかりません。スキップ")
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def parse_date_yyyy_mm_dd(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()

def normalize_payload(model_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    CSV 文字列をモデルに合わせて軽く整形（必要最低限）
    - 空文字 → None
    - 日付文字列 → date
    """
    r = {k: (v if v != "" else None) for k, v in row.items() if k != "id"}
    if model_name == "Party":
        r["founded_on"]   = parse_date_yyyy_mm_dd(r.get("founded_on"))
        r["dissolved_on"] = parse_date_yyyy_mm_dd(r.get("dissolved_on"))
    elif model_name == "Law":
        # Law側も日付カラム等があればここで変換
        pass
    return r

def upsert_simple_table(
    db: Session,
    model,
    rows: List[Dict[str, Any]],
    uniq_cols: List[str],
    dry_run: bool = False,
):
    """
    id は CSV からは受け取らず常に自動生成（CHAR(18)）。
    業務キー（uniq_cols）にユニーク制約がある前提で、
    INSERT ... ON DUPLICATE KEY UPDATE を使用した冪等UPSERT。
    既存衝突時は id=id として PK を変更しない。
    """
    if not rows:
        return

    tbl = model.__table__
    for raw in rows:
        # 軽い整形（空文字→None、日付変換など）
        r = normalize_payload(model.__name__, raw)

        # 先に新規用 id を生成（既存に当たった場合はUPDATE側で id は変更しない）
        new_id = make_char18_id()
        values = {"id": new_id, **{k: v for k, v in r.items() if v is not None}}

        # INSERT 文（この時点では実行されない）
        ins = mysql_insert(tbl).values(**values)

        # 競合時に更新する列（uniq_cols と id を除外）
        update_cols = {
            c.name: ins.inserted[c.name]
            for c in tbl.c
            if c.name not in uniq_cols and c.name != "id"
        }
        # id は変更しない（= 自身に代入）
        update_cols["id"] = tbl.c.id  # id=id

        typer.echo(
            "→ UPSERT "
            f"{model.__name__}: " +
            "{" + ", ".join(f"{k}={r.get(k)}" for k in uniq_cols) + "}"
        )
        if not dry_run:
            db.execute(ins.on_duplicate_key_update(**update_cols))

def name_map(db: Session, model, key_col: str = "name") -> Dict[str, Any]:
    """model の name -> id の辞書を返す。"""
    stmt = select(getattr(model, key_col), model.id)
    return {k: v for k, v in db.execute(stmt).all()}

# ==============================================================
# seed utility main
# ==============================================================

# typer.Option() はコマンドライン引数をオプション型式で受け取るための装飾子
# 例：pa seed-master --seeds-dir seeds --dry-run True
@cli.command()
def seed_master(
    seeds_dir: str = typer.Option("seeds", help="シードCSVのディレクトリのパス"),
    dry_run: bool = typer.Option(False, help="実行せずログのみ"),
):
    """
    マスターデータを冪等投入（CHAR(18) id を自動生成）。
    親→子（中間）の順に投入します。
    """
    base = Path(seeds_dir)
    with SessionLocal() as db:
        # 1) 親テーブル
        parties    = read_csv(base / "Party.csv")       # 想定: name,short_name,founded_on,dissolved_on
        categories = read_csv(base / "Category.csv")    # 想定: name,description,...
        laws       = read_csv(base / "Law.csv")         # 想定: name,law_number,title,law_type,...

        # 一意キーを "name" に変更（DB側に UNIQUE(name) を推奨）
        upsert_simple_table(db, Party,    parties,    uniq_cols=["name"], dry_run=dry_run)
        upsert_simple_table(db, Category, categories, uniq_cols=["name"], dry_run=dry_run)
        upsert_simple_table(db, Law,      laws,      uniq_cols=["name"], dry_run=dry_run)

        # 2) 子・中間テーブル： PartyLawRole (party_id, law_id, role, note)
        plr_rows = read_csv(base / "party_law_roles.csv")  # 想定: party_name,law_name,role,note
        if plr_rows:
            party_name_to_id = name_map(db, Party, key_col="name")
            law_name_to_id   = name_map(db, Law,   key_col="name")

            for r in plr_rows:
                try:
                    party_id = party_name_to_id[r["party_name"]]
                    law_id   = law_name_to_id[r["law_name"]]
                except KeyError as e:
                    typer.echo(f"⚠ 参照先が見つかりません: {e}. 行をスキップ -> {r}")
                    continue

                role_val = r.get("role")
                role_obj = None
                if role_val:
                    try:
                        role_obj = PartyRole(role_val) if role_val in PartyRole._value2member_map_ else PartyRole[role_val]
                    except Exception:
                        typer.echo(f"⚠ role の値が不正です: {role_val}. 行をスキップ -> {r}")
                        continue

                payload = {
                    "party_id": party_id,
                    "law_id":   law_id,
                    "role":     role_obj,
                    "note":     r.get("note") or None,
                }

                tbl = PartyLawRole.__table__
                ins = mysql_insert(tbl).values(**payload)
                # 複合主キー (party_id, law_id, role) 前提：IDは存在しないので除外でOK
                update_cols = {
                    c.name: ins.inserted[c.name]
                    for c in tbl.c
                    if c.name not in ("party_id", "law_id", "role")
                }

                typer.echo(
                    f"→ UPSERT PartyLawRole: party_id={payload['party_id']}, "
                    f"law_id={payload['law_id']}, role={payload['role']}"
                )
                if not dry_run:
                    db.execute(ins.on_duplicate_key_update(**update_cols))

        if not dry_run:
            db.commit()

    typer.echo("✅ シード投入（CHAR(18) id 自動生成）完了")

#################################################################
# 以下は、モデル名を指定してレコードを表示するユーティリティ
#################################################################
from typing import Optional
from sqlalchemy import desc as sa_desc
import json
#
#
#
# モデル名 → クラス のレジストリ（明示的に）
MODEL_REGISTRY: Dict[str, Any] = {
    "Party": Party,
    "Category": Category,
    "Law": Law,
    "PartyLawRole": PartyLawRole,
}

def _serialize_value(v: Any) -> Any:
    """JSON/表出力向けの軽いシリアライザ"""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    # SQLAlchemy Enum は Python Enum になる想定
    try:
        from enum import Enum
        if isinstance(v, Enum):
            return v.value
    except Exception:
        pass
    return v

def _row_to_dict(obj) -> Dict[str, Any]:
    """モデルインスタンス -> 辞書（テーブル列のみ）"""
    cols = obj.__table__.columns.keys()
    return {c: _serialize_value(getattr(obj, c)) for c in cols}

def _parse_value(s: str) -> Any:
    """--where col=value の value を型推定（int/float/日付YYYY-MM-DD/その他）"""
    s = s.strip()
    # 日付簡易判定
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s)
        except Exception:
            pass
    # 数値
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        try:
            return int(s)
        except Exception:
            pass
    try:
        return float(s)
    except Exception:
        return s  # 文字列

@cli.command("show")
def show_records(
    model: str = typer.Argument(..., help="モデル名（例: Party / Category / Law / PartyLawRole）"),
    limit: int = typer.Option(20, "--limit", "-n", help="最大取得件数"),
    columns: Optional[str] = typer.Option(None, "--columns", "-c", help="表示する列をカンマ区切りで指定（未指定は全列）"),
    order_by: str = typer.Option("id", "--order-by", "-o", help="並び替え列名（既定: id）"),
    desc: bool = typer.Option(False, "--desc", help="降順にする"),
    where: List[str] = typer.Option(None, "--where", "-w", help="等価条件（col=value）。複数指定可"),
    output: str = typer.Option("table", "--output", "-f", help="出力形式: table | json", case_sensitive=False),
):
    """
    指定モデルのレコードを表示する簡易ビューア。
    例:
      pa show Party -n 10
      pa show Category --columns name,description --order-by name
      pa show Law -w name=日本国憲法 -f json
    """
    Model = MODEL_REGISTRY.get(model)
    if Model is None:
        valid = ", ".join(MODEL_REGISTRY.keys())
        typer.echo(f"❌ 未知のモデル名です: {model} （候補: {valid}）")
        raise typer.Exit(code=1)

    # 列バリデーション
    all_cols = list(Model.__table__.columns.keys())
    if columns:
        selected_cols = [c.strip() for c in columns.split(",") if c.strip()]
        unknown = [c for c in selected_cols if c not in all_cols]
        if unknown:
            typer.echo(f"❌ 未知の列があります: {unknown}  （利用可能: {all_cols}）")
            raise typer.Exit(code=1)
    else:
        selected_cols = all_cols

    # order_by の列チェック
    if order_by not in all_cols:
        typer.echo(f"❌ order_by 列が不正です: {order_by} （利用可能: {all_cols}）")
        raise typer.Exit(code=1)

    # where 条件（等価のみ対応）
    where_clauses = []
    if where:
        for expr in where:
            if "=" not in expr:
                typer.echo(f"⚠ 条件を無視しました（col=value 形式ではありません）: {expr}")
                continue
            k, v = expr.split("=", 1)
            k = k.strip()
            if k not in all_cols:
                typer.echo(f"⚠ 未知の列の条件を無視しました: {k}")
                continue
            col = getattr(Model, k)
            where_clauses.append(col == _parse_value(v))

    # クエリ組み立て
    stmt = select(Model)
    if where_clauses:
        stmt = stmt.where(*where_clauses)
    order_col = getattr(Model, order_by)
    stmt = stmt.order_by(sa_desc(order_col) if desc else order_col)
    if limit:
        stmt = stmt.limit(limit)

    # 実行
    with SessionLocal() as db:
        rows = db.execute(stmt).scalars().all()

    # 整形
    dict_rows = [{k: _serialize_value(v) for k, v in _row_to_dict(r).items()} for r in rows]

    if output.lower() == "json":
        typer.echo(json.dumps(
            [{k: v for k, v in d.items() if k in selected_cols} for d in dict_rows],
            ensure_ascii=False, indent=2
        ))
        return

    # table 出力（簡易）
    widths = {c: max(len(c), *(len(str(d.get(c, ""))) for d in dict_rows)) for c in selected_cols}
    header = " | ".join(c.ljust(widths[c]) for c in selected_cols)
    sep = "-+-".join("-" * widths[c] for c in selected_cols)
    typer.echo(header)
    typer.echo(sep)
    for d in dict_rows:
        line = " | ".join(str(d.get(c, "")).ljust(widths[c]) for c in selected_cols)
        typer.echo(line)


if __name__ == "__main__":
    cli()