from __future__ import annotations

import argparse
import math
import os
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import xml.etree.ElementTree as ET

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as exc:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
    TK_IMPORT_ERROR = exc
else:
    TK_IMPORT_ERROR = None


BASE_DIR = Path(__file__).resolve().parent
APP_ASSETS_DIR = BASE_DIR / "app_assets"
PRODUCT_IMAGES_DIR = APP_ASSETS_DIR / "product_images"
PRODUCTS_XLSX = APP_ASSETS_DIR / "Tovar.xlsx"
USERS_XLSX = APP_ASSETS_DIR / "user_import.xlsx"
PICKUP_POINTS_XLSX = APP_ASSETS_DIR / "Пункты выдачи_import.xlsx"
ORDERS_XLSX = APP_ASSETS_DIR / "Заказ_import.xlsx"


def _resolve_db_path() -> Path:
    script_path = str(Path(__file__))
    if os.name == "nt" and script_path.startswith("\\\\"):
        local_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StroyMaterialy_v326"
        local_dir.mkdir(parents=True, exist_ok=True)
        return local_dir / "store.db"
    return BASE_DIR / "store.db"


DB_PATH = _resolve_db_path()

WHITE = "#FFFFFF"
GOLD = "#DAA520"
ACCENT = "#B8860B"
DISCOUNT_BG = "#F4A460"
OUT_OF_STOCK_BG = "#BFEFFF"
FONT = ("Calibri", 12)
TITLE_FONT = ("Calibri", 18, "bold")
SMALL_FONT = ("Calibri", 10)
SUPPORTED_TK_IMAGE_SUFFIXES = {".png", ".gif", ".pgm", ".ppm"}

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

SORT_FIELDS = {
    "Без сортировки": None,
    "Количество": "stock_quantity",
    "Цена": "price",
    "Скидка": "discount",
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def _remove_database_files() -> None:
    for suffix in ("", "-wal", "-shm", "-journal"):
        path = Path(f"{DB_PATH}{suffix}")
        if path.exists():
            path.unlink()


def initialize_database(reset: bool = False) -> None:
    if reset:
        _remove_database_files()
    elif DB_PATH.exists() and DB_PATH.stat().st_size == 0:
        _remove_database_files()

    APP_ASSETS_DIR.mkdir(exist_ok=True)
    PRODUCT_IMAGES_DIR.mkdir(exist_ok=True)

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


def _import_products(connection: sqlite3.Connection) -> None:
    rows = _read_xlsx(PRODUCTS_XLSX)
    for row in rows[1:]:
        if len(row) < 11 or not row[0].strip():
            continue

        article = row[0].strip()
        name = row[1].strip()
        unit_id = _get_or_create_lookup(connection, "units", row[2].strip())
        price = _safe_float(row[3])
        supplier_id = _get_or_create_lookup(connection, "suppliers", row[4].strip())
        manufacturer_id = _get_or_create_lookup(connection, "manufacturers", row[5].strip())
        category_id = _get_or_create_lookup(connection, "categories", row[6].strip())
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
    rows = _read_xlsx(USERS_XLSX)
    for row in rows[1:]:
        if len(row) < 4 or not row[2].strip():
            continue
        role_id = _get_or_create_lookup(connection, "roles", row[0].strip())
        connection.execute(
            """
            INSERT OR IGNORE INTO users (role_id, full_name, login, password)
            VALUES (?, ?, ?, ?)
            """,
            (role_id, row[1].strip(), row[2].strip(), row[3].strip()),
        )


def _import_pickup_points(connection: sqlite3.Connection) -> None:
    rows = _read_xlsx(PICKUP_POINTS_XLSX)
    for row in rows:
        if row and row[0].strip():
            connection.execute(
                "INSERT OR IGNORE INTO pickup_points (address) VALUES (?)",
                (row[0].strip(),),
            )


def _import_orders(connection: sqlite3.Connection) -> None:
    rows = _read_xlsx(ORDERS_XLSX)
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



XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _read_xlsx(path: Path) -> list[list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл импорта: {path}")

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


def _get_or_create_lookup(connection: sqlite3.Connection, table: str, name: str) -> int:
    clean_name = name.strip() or "Не указано"
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


def authenticate(login: str, password: str) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            """
            SELECT users.id, users.full_name, users.login, roles.name AS role
            FROM users
            JOIN roles ON roles.id = users.role_id
            WHERE users.login = ? AND users.password = ?
            """,
            (login.strip(), password.strip()),
        ).fetchone()


def get_products(
    search: str = "",
    manufacturer: str = "Все производители",
    sort_label: str = "Без сортировки",
    sort_direction: str = "По возрастанию",
) -> list[sqlite3.Row]:
    query = """
        SELECT
            products.article,
            products.name,
            products.price,
            products.discount,
            products.stock_quantity,
            products.description,
            products.image_path,
            units.name AS unit,
            suppliers.name AS supplier,
            manufacturers.name AS manufacturer,
            categories.name AS category
        FROM products
        JOIN units ON units.id = products.unit_id
        JOIN suppliers ON suppliers.id = products.supplier_id
        JOIN manufacturers ON manufacturers.id = products.manufacturer_id
        JOIN categories ON categories.id = products.category_id
    """
    where: list[str] = []
    params: list[str] = []

    if search.strip():
        pattern = f"%{search.strip().lower()}%"
        where.append(
            """
            (
                lower(products.article) LIKE ?
                OR lower(products.name) LIKE ?
                OR lower(products.description) LIKE ?
                OR lower(units.name) LIKE ?
                OR lower(suppliers.name) LIKE ?
                OR lower(manufacturers.name) LIKE ?
                OR lower(categories.name) LIKE ?
            )
            """
        )
        params.extend([pattern] * 7)

    if manufacturer and manufacturer != "Все производители":
        where.append("manufacturers.name = ?")
        params.append(manufacturer)

    if where:
        query += " WHERE " + " AND ".join(where)

    sort_field = SORT_FIELDS.get(sort_label)
    if sort_field:
        direction = "DESC" if sort_direction == "По убыванию" else "ASC"
        query += f" ORDER BY products.{sort_field} {direction}, products.name ASC"
    else:
        query += " ORDER BY products.name ASC"

    with connect() as connection:
        return list(connection.execute(query, params).fetchall())


def get_product(article: str | None) -> sqlite3.Row | None:
    if article is None:
        return None
    with connect() as connection:
        return connection.execute(
            """
            SELECT
                products.article,
                products.name,
                products.price,
                products.discount,
                products.stock_quantity,
                products.description,
                products.image_path,
                units.name AS unit,
                suppliers.name AS supplier,
                manufacturers.name AS manufacturer,
                categories.name AS category
            FROM products
            JOIN units ON units.id = products.unit_id
            JOIN suppliers ON suppliers.id = products.supplier_id
            JOIN manufacturers ON manufacturers.id = products.manufacturer_id
            JOIN categories ON categories.id = products.category_id
            WHERE products.article = ?
            """,
            (article,),
        ).fetchone()


def get_manufacturers() -> list[str]:
    with connect() as connection:
        rows = connection.execute("SELECT name FROM manufacturers ORDER BY name").fetchall()
    return ["Все производители"] + [row["name"] for row in rows]


def get_lookup_values(table: str) -> list[str]:
    if table not in {"categories", "manufacturers", "suppliers", "units"}:
        raise ValueError("Unsupported lookup table")
    with connect() as connection:
        rows = connection.execute(f"SELECT name FROM {table} ORDER BY name").fetchall()
    return [row["name"] for row in rows]


def get_orders() -> list[sqlite3.Row]:
    with connect() as connection:
        return list(
            connection.execute(
                """
                SELECT
                    orders.id,
                    orders.order_date,
                    orders.delivery_date,
                    pickup_points.address AS pickup_point,
                    orders.client_name,
                    orders.pickup_code,
                    orders.status,
                    group_concat(order_items.product_article || ' x' || order_items.quantity, ', ') AS items
                FROM orders
                LEFT JOIN pickup_points ON pickup_points.id = orders.pickup_point_id
                LEFT JOIN order_items ON order_items.order_id = orders.id
                GROUP BY orders.id
                ORDER BY orders.id
                """
            ).fetchall()
        )


def save_product(product: dict[str, object], is_new: bool) -> None:
    with connect() as connection:
        category_id = _get_or_create_lookup(connection, "categories", str(product["category"]))
        manufacturer_id = _get_or_create_lookup(connection, "manufacturers", str(product["manufacturer"]))
        supplier_id = _get_or_create_lookup(connection, "suppliers", str(product["supplier"]))
        unit_id = _get_or_create_lookup(connection, "units", str(product["unit"]))

        if is_new:
            connection.execute(
                """
                INSERT INTO products (
                    article, name, unit_id, price, supplier_id, manufacturer_id,
                    category_id, discount, stock_quantity, description, image_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product["article"],
                    product["name"],
                    unit_id,
                    product["price"],
                    supplier_id,
                    manufacturer_id,
                    category_id,
                    product["discount"],
                    product["stock_quantity"],
                    product["description"],
                    product["image_path"],
                ),
            )
        else:
            connection.execute(
                """
                UPDATE products
                SET
                    name = ?,
                    unit_id = ?,
                    price = ?,
                    supplier_id = ?,
                    manufacturer_id = ?,
                    category_id = ?,
                    discount = ?,
                    stock_quantity = ?,
                    description = ?,
                    image_path = ?
                WHERE article = ?
                """,
                (
                    product["name"],
                    unit_id,
                    product["price"],
                    supplier_id,
                    manufacturer_id,
                    category_id,
                    product["discount"],
                    product["stock_quantity"],
                    product["description"],
                    product["image_path"],
                    product["article"],
                ),
            )
        connection.commit()


def delete_product(article: str) -> tuple[bool, str]:
    with connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM order_items WHERE product_article = ?",
            (article,),
        ).fetchone()
        if row and int(row["count"]) > 0:
            return False, "Товар присутствует в заказе, поэтому удалить его нельзя."
        product = get_product(article)
        connection.execute("DELETE FROM products WHERE article = ?", (article,))
        connection.commit()
    _delete_managed_image(product["image_path"] if product else None)
    return True, "Товар удален."


def article_exists(article: str) -> bool:
    with connect() as connection:
        return connection.execute(
            "SELECT 1 FROM products WHERE article = ?",
            (article,),
        ).fetchone() is not None


def generate_article() -> str:
    with connect() as connection:
        count = int(connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]) + 1
    while True:
        article = f"P{count:05d}"
        if not article_exists(article):
            return article
        count += 1


def _delete_managed_image(image_path: str | None) -> None:
    if not image_path or not image_path.startswith("app_assets/product_images/"):
        return
    path = BASE_DIR / image_path
    if path.exists():
        path.unlink()


def _resolved_image_path(image_path: str | None) -> Path:
    if image_path:
        candidate = Path(image_path)
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        if candidate.exists():
            return candidate
    return APP_ASSETS_DIR / "picture.png"


def _can_render_with_tk(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_TK_IMAGE_SUFFIXES and path.exists()


def load_tk_image(path: Path, max_size: tuple[int, int] | None = None) -> tk.PhotoImage:
    image = tk.PhotoImage(file=str(path))
    if max_size is None:
        return image

    max_width, max_height = max_size
    width_ratio = math.ceil(image.width() / max_width) if image.width() > max_width else 1
    height_ratio = math.ceil(image.height() / max_height) if image.height() > max_height else 1
    factor = max(width_ratio, height_ratio, 1)
    if factor > 1:
        image = image.subsample(factor, factor)
    return image


if tk is None:
    class StoreApp:
        pass
else:
    class StoreApp(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title("СтройМатериалы - вход")
            self.geometry("1120x720")
            self.configure(bg=WHITE)
            self.current_user: dict[str, str] | None = None
            self.edit_window: ProductForm | None = None
            self.product_images: list[tk.PhotoImage] = []

            icon_path = APP_ASSETS_DIR / "icon.png"
            if _can_render_with_tk(icon_path):
                self.iconphoto(True, load_tk_image(icon_path))

            self.container = tk.Frame(self, bg=WHITE)
            self.container.pack(fill="both", expand=True)
            self.show_login()

        def clear(self) -> None:
            for child in self.container.winfo_children():
                child.destroy()

        def show_login(self) -> None:
            self.current_user = None
            self.title("СтройМатериалы - вход")
            self.clear()
            LoginFrame(self.container, self).pack(fill="both", expand=True)

        def login(self, login: str, password: str) -> None:
            user = authenticate(login, password)
            if user is None:
                messagebox.showerror(
                    "Ошибка авторизации",
                    "Пользователь с указанным логином и паролем не найден. "
                    "Проверьте введенные данные и повторите попытку.",
                )
                return
            self.current_user = {
                "full_name": user["full_name"],
                "role": user["role"],
            }
            self.show_products()

        def guest_login(self) -> None:
            self.current_user = {
                "full_name": "Гость",
                "role": "Гость",
            }
            self.show_products()

        def show_products(self) -> None:
            self.title("СтройМатериалы - список товаров")
            self.clear()
            ProductListFrame(self.container, self).pack(fill="both", expand=True)

        def show_orders(self) -> None:
            self.title("СтройМатериалы - заказы")
            self.clear()
            OrdersFrame(self.container, self).pack(fill="both", expand=True)

        @property
        def role(self) -> str:
            return self.current_user["role"] if self.current_user else "Гость"

        @property
        def full_name(self) -> str:
            return self.current_user["full_name"] if self.current_user else "Гость"


    class LoginFrame(tk.Frame):
        def __init__(self, parent: tk.Widget, app: StoreApp) -> None:
            super().__init__(parent, bg=WHITE)
            self.app = app
            self.login_var = tk.StringVar()
            self.password_var = tk.StringVar()
            self.logo: tk.PhotoImage | None = None

            content = tk.Frame(self, bg=WHITE)
            content.place(relx=0.5, rely=0.5, anchor="center")

            logo_path = APP_ASSETS_DIR / "icon.png"
            if _can_render_with_tk(logo_path):
                self.logo = load_tk_image(logo_path, (160, 130))
                tk.Label(content, image=self.logo, bg=WHITE).pack(pady=(0, 12))

            tk.Label(content, text="СтройМатериалы", bg=WHITE, font=TITLE_FONT).pack(pady=(0, 18))
            form = tk.Frame(content, bg=GOLD, padx=28, pady=24)
            form.pack()

            tk.Label(form, text="Логин", bg=GOLD, font=FONT).grid(row=0, column=0, sticky="w", pady=6)
            tk.Entry(form, textvariable=self.login_var, font=FONT, width=34).grid(row=1, column=0, pady=(0, 12))
            tk.Label(form, text="Пароль", bg=GOLD, font=FONT).grid(row=2, column=0, sticky="w", pady=6)
            tk.Entry(form, textvariable=self.password_var, show="*", font=FONT, width=34).grid(row=3, column=0, pady=(0, 18))
            accent_button(form, "Войти", self._login).grid(row=4, column=0, sticky="ew", pady=4)
            tk.Button(
                form,
                text="Войти как гость",
                command=self.app.guest_login,
                font=FONT,
                bg=WHITE,
                relief="flat",
            ).grid(row=5, column=0, sticky="ew", pady=4)

        def _login(self) -> None:
            self.app.login(self.login_var.get(), self.password_var.get())


    class Header(tk.Frame):
        def __init__(self, parent: tk.Widget, app: StoreApp, title: str) -> None:
            super().__init__(parent, bg=GOLD, padx=16, pady=10)
            tk.Label(self, text=title, bg=GOLD, font=TITLE_FONT).pack(side="left")
            right = tk.Frame(self, bg=GOLD)
            right.pack(side="right")
            tk.Label(right, text=app.full_name, bg=GOLD, font=FONT).pack(side="left", padx=10)
            tk.Button(right, text="Выйти", command=app.show_login, font=FONT, bg=WHITE, relief="flat").pack(side="left")


    class ProductListFrame(tk.Frame):
        def __init__(self, parent: tk.Widget, app: StoreApp) -> None:
            super().__init__(parent, bg=WHITE)
            self.app = app
            self.search_var = tk.StringVar()
            self.manufacturer_var = tk.StringVar(value="Все производители")
            self.sort_var = tk.StringVar(value="Без сортировки")
            self.direction_var = tk.StringVar(value="По возрастанию")

            Header(self, app, "Список товаров").pack(fill="x")
            self._build_toolbar()
            self._build_scroll_area()
            self.refresh()

        def _build_toolbar(self) -> None:
            toolbar = tk.Frame(self, bg=WHITE, padx=12, pady=10)
            toolbar.pack(fill="x")

            if self.app.role in {"Менеджер", "Администратор"}:
                tk.Label(toolbar, text="Поиск", bg=WHITE, font=FONT).pack(side="left")
                tk.Entry(toolbar, textvariable=self.search_var, font=FONT, width=26).pack(side="left", padx=(6, 12))

                ttk.Combobox(
                    toolbar,
                    textvariable=self.manufacturer_var,
                    values=get_manufacturers(),
                    state="readonly",
                    width=24,
                    font=FONT,
                ).pack(side="left", padx=6)

                ttk.Combobox(
                    toolbar,
                    textvariable=self.sort_var,
                    values=list(SORT_FIELDS.keys()),
                    state="readonly",
                    width=18,
                    font=FONT,
                ).pack(side="left", padx=6)
                ttk.Combobox(
                    toolbar,
                    textvariable=self.direction_var,
                    values=["По возрастанию", "По убыванию"],
                    state="readonly",
                    width=16,
                    font=FONT,
                ).pack(side="left", padx=6)

                for variable in (
                    self.search_var,
                    self.manufacturer_var,
                    self.sort_var,
                    self.direction_var,
                ):
                    variable.trace_add("write", lambda *_: self.refresh())

            if self.app.role == "Администратор":
                accent_button(toolbar, "Добавить товар", self.open_add_form).pack(side="right", padx=6)

            if self.app.role in {"Менеджер", "Администратор"}:
                tk.Button(toolbar, text="Заказы", command=self.app.show_orders, font=FONT, bg=WHITE, relief="flat").pack(
                    side="right",
                    padx=6,
                )

        def _build_scroll_area(self) -> None:
            wrapper = tk.Frame(self, bg=WHITE)
            wrapper.pack(fill="both", expand=True, padx=12, pady=(0, 12))

            self.canvas = tk.Canvas(wrapper, bg=WHITE, highlightthickness=0)
            scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=self.canvas.yview)
            self.list_frame = tk.Frame(self.canvas, bg=WHITE)
            self.list_frame.bind(
                "<Configure>",
                lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
            )
            self.canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
            self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfig(self.canvas_window, width=event.width))
            self.canvas.configure(yscrollcommand=scrollbar.set)
            self.canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

        def refresh(self) -> None:
            for child in self.list_frame.winfo_children():
                child.destroy()
            self.app.product_images.clear()

            products = get_products(
                self.search_var.get(),
                self.manufacturer_var.get(),
                self.sort_var.get(),
                self.direction_var.get(),
            )
            if not products:
                tk.Label(
                    self.list_frame,
                    text="Товары не найдены",
                    bg=WHITE,
                    font=TITLE_FONT,
                ).pack(pady=40)
                return

            for product in products:
                self._product_row(product).pack(fill="x", pady=5)

        def _product_row(self, product: sqlite3.Row) -> tk.Frame:
            bg = WHITE
            if int(product["stock_quantity"]) == 0:
                bg = OUT_OF_STOCK_BG
            elif float(product["discount"]) > 12:
                bg = DISCOUNT_BG

            row = tk.Frame(self.list_frame, bg=bg, padx=10, pady=10, highlightbackground=GOLD, highlightthickness=1)
            image = self._load_product_image(product["image_path"])
            self.app.product_images.append(image)
            tk.Label(row, image=image, bg=bg).pack(side="left", padx=(0, 12))

            info = tk.Frame(row, bg=bg)
            info.pack(side="left", fill="both", expand=True)
            tk.Label(info, text=f"{product['name']} ({product['article']})", bg=bg, font=("Calibri", 14, "bold")).pack(
                anchor="w"
            )
            tk.Label(info, text=product["description"], bg=bg, font=FONT, wraplength=560, justify="left").pack(anchor="w")
            details = (
                f"Категория: {product['category']} | Производитель: {product['manufacturer']} | "
                f"Поставщик: {product['supplier']} | Ед.: {product['unit']}"
            )
            tk.Label(info, text=details, bg=bg, font=SMALL_FONT).pack(anchor="w", pady=(4, 0))
            tk.Label(
                info,
                text=f"На складе: {product['stock_quantity']} | Скидка: {product['discount']:g}%",
                bg=bg,
                font=SMALL_FONT,
            ).pack(anchor="w")

            price_frame = tk.Frame(row, bg=bg)
            price_frame.pack(side="right", padx=8)
            if float(product["discount"]) > 0:
                old_font = ("Calibri", 12, "overstrike")
                tk.Label(price_frame, text=f"{product['price']:.2f}", fg="red", bg=bg, font=old_font).pack(anchor="e")
                final_price = float(product["price"]) * (1 - float(product["discount"]) / 100)
                tk.Label(price_frame, text=f"{final_price:.2f}", fg="black", bg=bg, font=("Calibri", 14, "bold")).pack(
                    anchor="e"
                )
            else:
                tk.Label(price_frame, text=f"{product['price']:.2f}", bg=bg, font=("Calibri", 14, "bold")).pack(anchor="e")

            if self.app.role == "Администратор":
                row.bind("<Button-1>", lambda _event, article=product["article"]: self.open_edit_form(article))
                for child in row.winfo_children():
                    child.bind("<Button-1>", lambda _event, article=product["article"]: self.open_edit_form(article))
                tk.Button(
                    price_frame,
                    text="Удалить",
                    font=SMALL_FONT,
                    command=lambda article=product["article"]: self.delete_product(article),
                    bg=WHITE,
                ).pack(anchor="e", pady=(8, 0))
            return row

        def _load_product_image(self, image_path: str | None) -> tk.PhotoImage:
            path = _resolved_image_path(image_path)
            if not _can_render_with_tk(path):
                path = APP_ASSETS_DIR / "picture.png"
            return load_tk_image(path, (120, 90))

        def open_add_form(self) -> None:
            if self.app.edit_window and self.app.edit_window.winfo_exists():
                self.app.edit_window.focus()
                return
            self.app.edit_window = ProductForm(self.app, self, None)

        def open_edit_form(self, article: str) -> None:
            if self.app.edit_window and self.app.edit_window.winfo_exists():
                self.app.edit_window.focus()
                return
            self.app.edit_window = ProductForm(self.app, self, article)

        def delete_product(self, article: str) -> None:
            if not messagebox.askyesno(
                "Подтверждение удаления",
                "Удаление товара необратимо. Вы действительно хотите удалить выбранный товар?",
            ):
                return
            ok, message = delete_product(article)
            if ok:
                messagebox.showinfo("Удаление товара", message)
                self.refresh()
            else:
                messagebox.showwarning("Удаление запрещено", message)


    class ProductForm(tk.Toplevel):
        def __init__(self, app: StoreApp, list_frame: ProductListFrame, article: str | None) -> None:
            super().__init__(app)
            self.app = app
            self.list_frame = list_frame
            self.is_new = article is None
            self.product = get_product(article) if article else None
            self.selected_image_path = self.product["image_path"] if self.product else None
            self.preview_image: tk.PhotoImage | None = None
            self.title("Добавление товара" if self.is_new else "Редактирование товара")
            self.geometry("620x650")
            self.configure(bg=WHITE)
            self.protocol("WM_DELETE_WINDOW", self.close)

            self.values: dict[str, tk.StringVar] = {
                "article": tk.StringVar(value=generate_article() if self.is_new else self.product["article"]),
                "name": tk.StringVar(value="" if self.is_new else self.product["name"]),
                "category": tk.StringVar(value="" if self.is_new else self.product["category"]),
                "manufacturer": tk.StringVar(value="" if self.is_new else self.product["manufacturer"]),
                "supplier": tk.StringVar(value="" if self.is_new else self.product["supplier"]),
                "price": tk.StringVar(value="" if self.is_new else str(self.product["price"])),
                "unit": tk.StringVar(value="" if self.is_new else self.product["unit"]),
                "stock_quantity": tk.StringVar(value="" if self.is_new else str(self.product["stock_quantity"])),
                "discount": tk.StringVar(value="0" if self.is_new else str(self.product["discount"])),
            }
            self.description = tk.Text(self, height=4, font=FONT, wrap="word")
            self._build()

        def _build(self) -> None:
            title_bar = tk.Frame(self, bg=GOLD, padx=16, pady=10)
            title_bar.pack(fill="x")
            tk.Label(
                title_bar,
                text="Добавление товара" if self.is_new else "Редактирование товара",
                bg=GOLD,
                font=TITLE_FONT,
            ).pack(side="left")
            form = tk.Frame(self, bg=WHITE, padx=16, pady=12)
            form.pack(fill="both", expand=True)

            self.preview_label = tk.Label(form, bg=WHITE)
            self.preview_label.grid(row=0, column=0, rowspan=4, padx=(0, 18), sticky="n")
            self._refresh_preview()
            accent_button(form, "Выбрать PNG", self.choose_image).grid(row=4, column=0, sticky="ew", padx=(0, 18))

            self._entry(form, "Артикул", "article", 0, readonly=not self.is_new)
            self._entry(form, "Наименование", "name", 1)
            self._combo(form, "Категория", "category", get_lookup_values("categories"), 2)
            self._combo(form, "Производитель", "manufacturer", get_lookup_values("manufacturers"), 3)
            self._entry(form, "Поставщик", "supplier", 4)
            self._entry(form, "Цена", "price", 5)
            self._entry(form, "Единица измерения", "unit", 6)
            self._entry(form, "Количество", "stock_quantity", 7)
            self._entry(form, "Скидка", "discount", 8)

            tk.Label(form, text="Описание", bg=WHITE, font=FONT).grid(row=9, column=0, sticky="w", pady=6)
            self.description.grid(row=9, column=1, columnspan=2, sticky="ew", pady=6)
            if self.product:
                self.description.insert("1.0", self.product["description"])

            buttons = tk.Frame(form, bg=WHITE)
            buttons.grid(row=10, column=0, columnspan=3, sticky="e", pady=18)
            tk.Button(buttons, text="Отмена", command=self.close, font=FONT, bg=WHITE).pack(side="left", padx=8)
            accent_button(buttons, "Сохранить", self.save).pack(side="left")
            form.columnconfigure(2, weight=1)

        def _entry(self, parent: tk.Widget, label: str, key: str, row: int, readonly: bool = False) -> None:
            tk.Label(parent, text=label, bg=WHITE, font=FONT).grid(row=row, column=1, sticky="w", pady=4)
            state = "readonly" if readonly else "normal"
            tk.Entry(parent, textvariable=self.values[key], font=FONT, state=state).grid(row=row, column=2, sticky="ew", pady=4)

        def _combo(self, parent: tk.Widget, label: str, key: str, values: list[str], row: int) -> None:
            tk.Label(parent, text=label, bg=WHITE, font=FONT).grid(row=row, column=1, sticky="w", pady=4)
            ttk.Combobox(parent, textvariable=self.values[key], values=values, font=FONT).grid(
                row=row,
                column=2,
                sticky="ew",
                pady=4,
            )

        def choose_image(self) -> None:
            path = filedialog.askopenfilename(
                title="Выберите PNG-изображение товара",
                filetypes=[("PNG", "*.png"), ("Все файлы", "*.*")],
            )
            if not path:
                return

            selected = Path(path)
            if selected.suffix.lower() != ".png":
                messagebox.showerror("Неподдерживаемый формат", "Без Pillow поддерживаются только PNG-изображения.")
                return

            self.selected_image_path = path
            self._refresh_preview()

        def _refresh_preview(self) -> None:
            path = self._selected_image_absolute_path()
            if not _can_render_with_tk(path):
                path = APP_ASSETS_DIR / "picture.png"
            self.preview_image = load_tk_image(path, (160, 120))
            self.preview_label.configure(image=self.preview_image)

        def _selected_image_absolute_path(self) -> Path:
            return _resolved_image_path(self.selected_image_path)

        def save(self) -> None:
            try:
                product = self._validated_product()
                product["image_path"] = self._save_image()
                save_product(product, self.is_new)
            except ValueError as error:
                messagebox.showerror("Ошибка сохранения", str(error))
                return
            except Exception as error:
                messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить товар: {error}")
                return

            messagebox.showinfo("Сохранение товара", "Данные товара сохранены.")
            self.list_frame.refresh()
            self.close()

        def _validated_product(self) -> dict[str, object]:
            article = self.values["article"].get().strip()
            if not article:
                raise ValueError("Укажите артикул товара.")
            if self.is_new and article_exists(article):
                raise ValueError("Товар с таким артикулом уже существует. Укажите другой артикул.")

            name = self.values["name"].get().strip()
            if not name:
                raise ValueError("Укажите наименование товара.")

            try:
                price = float(self.values["price"].get().replace(",", "."))
            except ValueError as exc:
                raise ValueError("Цена должна быть числом.") from exc
            if price < 0:
                raise ValueError("Цена не может быть отрицательной.")

            try:
                stock_quantity = int(float(self.values["stock_quantity"].get().replace(",", ".")))
            except ValueError as exc:
                raise ValueError("Количество на складе должно быть целым числом.") from exc
            if stock_quantity < 0:
                raise ValueError("Количество на складе не может быть отрицательным.")

            try:
                discount = float(self.values["discount"].get().replace(",", "."))
            except ValueError as exc:
                raise ValueError("Скидка должна быть числом.") from exc
            if discount < 0 or discount > 100:
                raise ValueError("Скидка должна быть в диапазоне от 0 до 100.")

            required = ("category", "manufacturer", "supplier", "unit")
            for key in required:
                if not self.values[key].get().strip():
                    raise ValueError("Заполните категорию, производителя, поставщика и единицу измерения.")

            image_path = self.selected_image_path
            if image_path:
                image_candidate = _resolved_image_path(image_path)
                if image_candidate != APP_ASSETS_DIR / "picture.png" and image_candidate.suffix.lower() != ".png":
                    raise ValueError("Для новых изображений поддерживается только PNG.")

            return {
                "article": article,
                "name": name,
                "category": self.values["category"].get().strip(),
                "manufacturer": self.values["manufacturer"].get().strip(),
                "supplier": self.values["supplier"].get().strip(),
                "unit": self.values["unit"].get().strip(),
                "price": price,
                "stock_quantity": stock_quantity,
                "discount": discount,
                "description": self.description.get("1.0", "end").strip(),
                "image_path": image_path,
            }

        def _save_image(self) -> str | None:
            if not self.selected_image_path:
                return None

            selected_path = self._selected_image_absolute_path()
            if selected_path == APP_ASSETS_DIR / "picture.png":
                return None
            if selected_path.suffix.lower() != ".png":
                raise ValueError("Для новых изображений поддерживается только PNG.")

            try:
                relative_selected = selected_path.relative_to(BASE_DIR)
            except ValueError:
                relative_selected = None
            if relative_selected and str(relative_selected).startswith("app_assets/product_images/"):
                return str(relative_selected)

            article = self.values["article"].get().strip()
            target = PRODUCT_IMAGES_DIR / f"{article}.png"
            shutil.copy2(selected_path, target)

            old_path = self.product["image_path"] if self.product else None
            if old_path and old_path.startswith("app_assets/product_images/"):
                absolute_old_path = BASE_DIR / old_path
                if absolute_old_path.exists() and absolute_old_path != target:
                    absolute_old_path.unlink()

            return str(target.relative_to(BASE_DIR))

        def close(self) -> None:
            self.app.edit_window = None
            self.destroy()


    class OrdersFrame(tk.Frame):
        def __init__(self, parent: tk.Widget, app: StoreApp) -> None:
            super().__init__(parent, bg=WHITE)
            Header(self, app, "Заказы").pack(fill="x")
            toolbar = tk.Frame(self, bg=WHITE, padx=12, pady=10)
            toolbar.pack(fill="x")
            tk.Button(toolbar, text="Назад", command=app.show_products, font=FONT, bg=WHITE, relief="flat").pack(side="left")

            columns = ("id", "order_date", "delivery_date", "pickup_point", "client_name", "pickup_code", "status", "items")
            tree = ttk.Treeview(self, columns=columns, show="headings")
            headings = {
                "id": "Номер",
                "order_date": "Дата заказа",
                "delivery_date": "Дата доставки",
                "pickup_point": "Пункт выдачи",
                "client_name": "Клиент",
                "pickup_code": "Код",
                "status": "Статус",
                "items": "Состав",
            }
            for column, heading in headings.items():
                tree.heading(column, text=heading)
                tree.column(column, width=120 if column != "items" else 220)
            tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            for order in get_orders():
                tree.insert("", "end", values=[order[column] or "" for column in columns])


    def accent_button(parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT,
            fg="white",
            activebackground=GOLD,
            activeforeground="black",
            font=FONT,
            relief="flat",
            padx=12,
            pady=6,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="СтройМатериалы")
    parser.add_argument("--init-db", action="store_true", help="Создать и заполнить базу без запуска интерфейса")
    parser.add_argument("--reset-db", action="store_true", help="Пересоздать базу и заполнить ее заново")
    args = parser.parse_args()

    initialize_database(reset=args.reset_db)
    if args.init_db:
        return

    if TK_IMPORT_ERROR is not None:
        raise SystemExit(
            "Missing GUI dependency: 'tkinter'. "
            "Install the system package for Tk support for your Python interpreter, "
            "then run the app again."
        ) from TK_IMPORT_ERROR

    app = StoreApp()
    app.mainloop()


if __name__ == "__main__":
    main()
