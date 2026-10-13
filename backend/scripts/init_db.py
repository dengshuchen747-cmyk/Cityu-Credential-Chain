from app.core.database import Base, engine
from app import models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables are ready.")


if __name__ == "__main__":
    main()
