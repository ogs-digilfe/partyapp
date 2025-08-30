from partyapp.db.base import Base, engine

def init_db():
    """partyappdbにDBスキーマを作成（初回のみ使用）"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema created")

if __name__ == "__main__":
    init_db()