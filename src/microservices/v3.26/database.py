from __future__ import annotations

import argparse
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile


BASE_DIR = Path(__file__).resolve().parent
PREPARED_ASSETS_DIR = BASE_DIR / "prepared_assets"
APP_ASSETS_DIR = BASE_DIR / "app_assets"
PRODUCT_IMAGES_DIR = APP_ASSETS_DIR / "product_images"
DB_PATH = BASE_DIR / "store.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    full_name TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS manufacturers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pickup_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    article TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    unit_id INTEGER NOT NULL REFERENCES units(id),
    price REAL NOT NULL CHECK (price >= 0),
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    discount REAL NOT NULL DEFAULT 0 CHECK (discount >= 0 AND discount <= 100),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    description TEXT NOT NULL DEFAULT '',
    image_path TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    order_date TEXT,
    delivery_date TEXT,
    pickup_point_id INTEGER REFERENCES pickup_points(id),
    client_name TEXT NOT NULL,
    pickup_code TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_article TEXT NOT NULL REFERENCES products(article),
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);
"""


XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(reset: bool = False) -> None:
    if reset and DB_PATH.exists():
        DB_PATH.unlink()

    APP_ASSETS_DIR.mkdir(exist_ok=True)
    PRODUCT_IMAGES_DIR.mkdir(exist_ok=True)
    _copy_static_assets()
    SCHEMA_PATH.write_text(SCHEMA_SQL.strip() + "\n", encoding="utf-8")

    with connect() as connection:
        connection.executescript(SCHEMA_SQL)
        if _table_count(connection, "products") == 0:
            import_all(connection)


def import_all(connection: sqlite3.Connection) -> None:
    _import_products(connection)
    _import_users(connection)
    _import_pickup_points(connection)
    _import_orders(connection)
    connection.commit()


def _copy_static_assets() -> None:
    for name in ("picture.png", "icon.png", "icon.ico", "icon.jpg"):
        source = PREPARED_ASSETS_DIR / name
        if source.exists():
            shutil.copy2(source, APP_ASSETS_DIR / name)

    for source in PREPARED_ASSETS_DIR.iterdir():
        if source.suffix.lower() in {".jpg", ".jpeg", ".png"} and source.name not in {
            "picture.png",
            "icon.png",
            "icon.ico",
            "icon.jpg",
        }:
            shutil.copy2(source, PRODUCT_IMAGES_DIR / source.name)


def _import_products(connection: sqlite3.Connection) -> None:
    rows = _read_xlsx(PREPARED_ASSETS_DIR / "Tovar.xlsx")
    for row in rows[1:]:
        if len(row) < 11 or not row[0].strip():
            continue

        article = row[0].strip()
        name = row[1].strip()
        unit_id = _get_or_create(connection, "units", row[2].strip())
        price = _safe_float(row[3])
        supplier_id = _get_or_create(connection, "suppliers", row[4].strip())
        manufacturer_id = _get_or_create(connection, "manufacturers", row[5].strip())
        category_id = _get_or_create(connection, "categories", row[6].strip())
        discount = _safe_float(row[7])
        stock_quantity = _safe_int(row[8])
        description = row[9].strip()
        image_name = row[10].strip()
        image_path = f"app_assets/product_images/{image_name}" if image_name else None

        connection.execute(
            """
            INSERT OR REPLACE INTO products (
                article, name, unit_id, price, supplier_id, manufacturer_id,
                category_id, discount, stock_quantity, description, image_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article,
                name,
                unit_id,
                price,
                supplier_id,
                manufacturer_id,
                category_id,
                discount,
                stock_quantity,
                description,
                image_path,
            ),
        )


def _import_users(connection: sqlite3.Connection) -> None:
    rows = _read_xlsx(PREPARED_ASSETS_DIR / "user_import.xlsx")
    for row in rows[1:]:
        if len(row) < 4 or not row[2].strip():
            continue
        role_id = _get_or_create(connection, "roles", row[0].strip())
        connection.execute(
            """
            INSERT OR IGNORE INTO users (role_id, full_name, login, password)
            VALUES (?, ?, ?, ?)
            """,
            (role_id, row[1].strip(), row[2].strip(), row[3].strip()),
        )


def _import_pickup_points(connection: sqlite3.Connection) -> None:
    rows = _read_xlsx(PREPARED_ASSETS_DIR / "Пункты выдачи_import.xlsx")
    for row in rows:
        if row and row[0].strip():
            connection.execute(
                "INSERT OR IGNORE INTO pickup_points (address) VALUES (?)",
                (row[0].strip(),),
            )


def _import_orders(connection: sqlite3.Connection) -> None:
    rows = _read_xlsx(PREPARED_ASSETS_DIR / "Заказ_import.xlsx")
    for row in rows[1:]:
        if len(row) < 8 or not row[0].strip():
            continue

        order_id = _safe_int(row[0])
        order_date = _parse_excel_date(row[2])
        delivery_date = _parse_excel_date(row[3])
        pickup_point_id = _safe_int(row[4])
        client_name = row[5].strip()
        pickup_code = row[6].strip()
        status = row[7].strip()

        connection.execute(
            """
            INSERT OR REPLACE INTO orders (
                id, order_date, delivery_date, pickup_point_id,
                client_name, pickup_code, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (order_id, order_date, delivery_date, pickup_point_id, client_name, pickup_code, status),
        )

        connection.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        for article, quantity in _parse_order_items(row[1]):
            if _product_exists(connection, article):
                connection.execute(
                    """
                    INSERT INTO order_items (order_id, product_article, quantity)
                    VALUES (?, ?, ?)
                    """,
                    (order_id, article, quantity),
                )
            else:
                print(f"Пропущена позиция заказа {order_id}: товар {article} не найден")


def _get_or_create(connection: sqlite3.Connection, table: str, name: str) -> int:
    clean_name = name or "Не указано"
    row = connection.execute(f"SELECT id FROM {table} WHERE name = ?", (clean_name,)).fetchone()
    if row:
        return int(row["id"])
    cursor = connection.execute(f"INSERT INTO {table} (name) VALUES (?)", (clean_name,))
    return int(cursor.lastrowid)


def _product_exists(connection: sqlite3.Connection, article: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM products WHERE article = ?",
        (article,),
    ).fetchone() is not None


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _safe_float(value: str) -> float:
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return 0.0


def _safe_int(value: str) -> int:
    try:
        return int(float(str(value).replace(",", ".").strip()))
    except ValueError:
        return 0


def _parse_order_items(value: str) -> list[tuple[str, int]]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    items: list[tuple[str, int]] = []
    for index in range(0, len(parts) - 1, 2):
        items.append((parts[index], _safe_int(parts[index + 1])))
    return items


def _parse_excel_date(value: str) -> str | None:
    clean_value = str(value).strip()
    if not clean_value:
        return None

    try:
        if clean_value.replace(".", "", 1).isdigit():
            base = date(1899, 12, 30)
            return (base + timedelta(days=int(float(clean_value)))).isoformat()
        return datetime.strptime(clean_value, "%d.%m.%Y").date().isoformat()
    except ValueError:
        print(f"Некорректная дата импортирована как NULL: {clean_value}")
        return None


def _read_xlsx(path: Path) -> list[list[str]]:
    with ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_map = {
            relationship.attrib["Id"]: relationship.attrib["Target"]
            for relationship in relationships
        }
        first_sheet = workbook.find("a:sheets/a:sheet", XLSX_NS)
        if first_sheet is None:
            return []

        relationship_id = first_sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        target = relationship_map[relationship_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"

        worksheet = ET.fromstring(archive.read(target))
        result: list[list[str]] = []
        for row in worksheet.findall("a:sheetData/a:row", XLSX_NS):
            values: list[str] = []
            last_column = 0
            for cell in row.findall("a:c", XLSX_NS):
                column_index = _column_number(cell.attrib.get("r", "A"))
                values.extend([""] * (column_index - last_column - 1))
                last_column = column_index

                value_node = cell.find("a:v", XLSX_NS)
                value = value_node.text if value_node is not None and value_node.text else ""
                if cell.attrib.get("t") == "s" and value:
                    value = shared_strings[int(value)]
                values.append(value)
            if any(value.strip() for value in values):
                result.append(values)
        return result


def _read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.findall(".//a:t", XLSX_NS))
        for item in root.findall("a:si", XLSX_NS)
    ]


def _column_number(cell_reference: str) -> int:
    letters = "".join(character for character in cell_reference if character.isalpha())
    number = 0
    for letter in letters:
        number = number * 26 + ord(letter.upper()) - 64
    return number


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    initialize_database(reset=args.reset)
    with connect() as connection:
        print(f"Товаров: {_table_count(connection, 'products')}")
        print(f"Пользователей: {_table_count(connection, 'users')}")
        print(f"Заказов: {_table_count(connection, 'orders')}")
        print(f"Пунктов выдачи: {_table_count(connection, 'pickup_points')}")


if __name__ == "__main__":
    main()
