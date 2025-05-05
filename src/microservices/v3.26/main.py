from __future__ import annotations

import argparse

from database import initialize_database
from ui import StoreApp


def main() -> None:
    parser = argparse.ArgumentParser(description="СтройМатериалы")
    parser.add_argument("--init-db", action="store_true", help="Создать и заполнить базу без запуска интерфейса")
    parser.add_argument("--reset-db", action="store_true", help="Пересоздать базу и заполнить ее заново")
    args = parser.parse_args()

    initialize_database(reset=args.reset_db)
    if args.init_db:
        return

    app = StoreApp()
    app.mainloop()


if __name__ == "__main__":
    main()
