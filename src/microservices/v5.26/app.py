import base64
import math
import struct
import shutil
import sqlite3
import subprocess
import tkinter as tk
import zlib
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = BASE_DIR / "product_images"
DB_PATH = BASE_DIR / "furniture_store.db"
PLACEHOLDER_PATH = ASSETS_DIR / "picture.png"
LOGO_PATH = ASSETS_DIR / "icon.png"
APP_ICON_PATH = ASSETS_DIR / "icon.png"
PRODUCTS_IMPORT_PATH = ASSETS_DIR / "Tovar.xlsx"
USERS_IMPORT_PATH = ASSETS_DIR / "user_import.xlsx"
ORDERS_IMPORT_PATH = ASSETS_DIR / "Заказ_import.xlsx"
PRIMARY_BG = "#FFFFFF"
SECONDARY_BG = "#00FFFF"
ACCENT_BG = "#0000FF"
DISCOUNT_BG = "#008080"
FONT_FAMILY = "Calibri"
BASE_FONT = (FONT_FAMILY, 11)
TITLE_FONT = (FONT_FAMILY, 20, "bold")
SUBTITLE_FONT = (FONT_FAMILY, 16, "bold")
BUTTON_FONT = (FONT_FAMILY, 11, "bold")
DISCOUNT_RANGES = {
    "Все диапазоны": None,
    "0-10,99%": (0, 10.99),
    "11-14,99%": (11, 14.99),
    "15% и более": (15, None),
}


PLACEHOLDER_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAASwAAADICAYAAABS39xVAAAACXBIWXMAAAsTAAALEwEAmpwY"
    "AAAHZ0lEQVR4nO3dvY7cNhRAUcqsd7kK8mI8kSdxEicJXKR9ZznLyhHcQAkTX7Wg2cx4xJmA"
    "hkRZB2gBPy2v8/39AgAAwJ1+9gIAAGClGQAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZ"
    "EQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDM"
    "CAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDA"
    "LDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAA"
    "LDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIA"
    "AJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDID"
    "AIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgR"
    "AcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZ"
    "EQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDM"
    "CAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDA"
    "LDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAA"
    "LDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIA"
    "AJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDID"
    "AIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgR"
    "AcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZ"
    "EQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDM"
    "CAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDA"
    "LDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAA"
    "LDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIA"
    "AJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDID"
    "AIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgR"
    "AcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZ"
    "EQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDM"
    "CAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDA"
    "LDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAA"
    "LDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIA"
    "AJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDID"
    "AIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgR"
    "AcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZ"
    "EQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDM"
    "CAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDA"
    "LDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAA"
    "LDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIAAJgRAcDMCAAALDIDAIAZEQDALDIA"
    "AJgRAcDMCAAALDIDAIAVz/8AF0VMM/QTdcwAAAAASUVORK5CYII="
)
PLACEHOLDER_GIF_BASE64 = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="


def ensure_directories():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    PLACEHOLDER_PATH.write_bytes(base64.b64decode(PLACEHOLDER_GIF_BASE64))


def image_dimensions(path):
    data = Path(path).read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    image = tk.PhotoImage(file=path)
    return image.width(), image.height()


def png_chunk(chunk_type, data):
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def build_placeholder_png(width=300, height=200):
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            checker = ((x // 20) + (y // 20)) % 2
            if checker:
                row.extend((230, 234, 238))
            else:
                row.extend((246, 248, 250))
        rows.append(bytes(row))

    raw = b"".join(rows)
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        header
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )


def final_price(price, discount_percent):
    return round(price * (1 - discount_percent / 100), 2)


def price_text(price, discount_percent):
    if discount_percent <= 0:
        return f"{price:.2f} руб."
    return f"{price:.2f} -> {final_price(price, discount_percent):.2f} руб."


def accent_button(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=ACCENT_BG,
        fg="white",
        activebackground="#0000CC",
        activeforeground="white",
        relief=tk.FLAT,
        padx=12,
        pady=5,
        font=BUTTON_FONT,
        cursor="hand2",
    )


def plain_button(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=SECONDARY_BG,
        fg="black",
        activebackground="#20FFFF",
        activeforeground="black",
        relief=tk.FLAT,
        padx=12,
        pady=5,
        font=BASE_FONT,
        cursor="hand2",
    )


def load_photo(path, max_width=None, max_height=None):
    try:
        image = tk.PhotoImage(file=path)
    except tk.TclError:
        image = load_png_photo(path, max_width, max_height)
        return image

    if max_width and max_height:
        while image.width() > max_width or image.height() > max_height:
            image = image.subsample(2, 2)
    return image


def paeth_predictor(left, up, upper_left):
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def load_png_photo(path, max_width=None, max_height=None):
    data = Path(path).read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None

    offset = 8
    width = height = color_type = bit_depth = None
    compressed = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_data = data[offset + 8:offset + 8 + length]
        offset += length + 12
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(">IIBBBBB", chunk_data)
            if bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
                return None
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if not compressed or width is None or height is None:
        return None

    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    rows = []
    previous = bytearray(stride)
    source = 0
    for _y in range(height):
        filter_type = raw[source]
        source += 1
        current = bytearray(raw[source:source + stride])
        source += stride
        for i, value in enumerate(current):
            left = current[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                current[i] = (value + left) & 0xFF
            elif filter_type == 2:
                current[i] = (value + up) & 0xFF
            elif filter_type == 3:
                current[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                current[i] = (value + paeth_predictor(left, up, upper_left)) & 0xFF
        rows.append(current)
        previous = current

    scale = 1
    if max_width and max_height:
        scale = max(1, math.ceil(max(width / max_width, height / max_height)))
    display_width = max(1, width // scale)
    display_height = max(1, height // scale)
    image = tk.PhotoImage(width=display_width, height=display_height)
    for y in range(display_height):
        row = rows[y * scale]
        colors = []
        for x in range(display_width):
            index = x * scale * channels
            red, green, blue = row[index], row[index + 1], row[index + 2]
            if channels == 4:
                alpha = row[index + 3] / 255
                red = round(red * alpha + 255 * (1 - alpha))
                green = round(green * alpha + 255 * (1 - alpha))
                blue = round(blue * alpha + 255 * (1 - alpha))
            colors.append(f"#{red:02x}{green:02x}{blue:02x}")
        image.put("{" + " ".join(colors) + "}", to=(0, y))
    return image


def column_index(cell_ref):
    letters = "".join(char for char in cell_ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index - 1


def read_xlsx_rows(path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", ns):
                shared_strings.append("".join(text.text or "" for text in item.findall(".//m:t", ns)))

        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows = []
    for row in sheet.findall(".//m:sheetData/m:row", ns):
        values = []
        for cell in row.findall("m:c", ns):
            index = column_index(cell.attrib["r"])
            while len(values) <= index:
                values.append(None)

            value_node = cell.find("m:v", ns)
            inline_node = cell.find("m:is/m:t", ns)
            if inline_node is not None:
                value = inline_node.text or ""
            elif value_node is None:
                value = None
            elif cell.attrib.get("t") == "s":
                value = shared_strings[int(value_node.text)]
            else:
                raw = value_node.text
                value = float(raw) if "." in raw else int(raw)
            values[index] = value
        rows.append(values)
    return rows


def row_dicts(path):
    rows = read_xlsx_rows(path)
    if not rows:
        return []
    headers = [str(header).strip() if header is not None else "" for header in rows[0]]
    result = []
    for row in rows[1:]:
        item = {}
        for index, header in enumerate(headers):
            if header:
                item[header] = row[index] if index < len(row) else None
        result.append(item)
    return result


def find_asset_path(name):
    if not name:
        return None
    expected = ASSETS_DIR / str(name)
    if expected.exists():
        return prepare_display_image(expected)
    needle = str(name).casefold()
    for path in ASSETS_DIR.iterdir():
        if path.name.casefold() == needle:
            return prepare_display_image(path)
    return None


def prepare_display_image(path):
    path = Path(path)
    if path.suffix.casefold() not in {".jpg", ".jpeg"}:
        return str(path.relative_to(BASE_DIR))

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    target = IMAGES_DIR / f"{path.stem}.png"
    if target.exists() and target.stat().st_mtime >= path.stat().st_mtime:
        return str(target.relative_to(BASE_DIR))

    try:
        subprocess.run(
            ["sips", "-s", "format", "png", str(path), "--out", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return str(path.relative_to(BASE_DIR))
    return str(target.relative_to(BASE_DIR))


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.init_schema()
        self.seed_demo_data()
        self.migrate_image_paths()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self):
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_id INTEGER NOT NULL REFERENCES roles(id),
                    login TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    full_name TEXT NOT NULL
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

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article TEXT NOT NULL UNIQUE,
                    category_id INTEGER NOT NULL REFERENCES categories(id),
                    manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
                    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    price REAL NOT NULL CHECK (price >= 0),
                    unit TEXT NOT NULL,
                    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
                    discount_percent REAL NOT NULL CHECK (discount_percent >= 0),
                    image_path TEXT
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Новый'
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL CHECK (quantity > 0)
                );
                """
            )

    def seed_demo_data(self):
        with self.connect() as connection:
            exists = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if exists:
                return

            if PRODUCTS_IMPORT_PATH.exists() and USERS_IMPORT_PATH.exists():
                self.seed_imported_data(connection)
                return

            roles = [
                ("client", "Клиент"),
                ("manager", "Менеджер"),
                ("admin", "Администратор"),
            ]
            connection.executemany("INSERT INTO roles (code, name) VALUES (?, ?)", roles)

            users = [
                (1, "client", "client", "Смирнова Алиса Игоревна"),
                (2, "manager", "manager", "Петров Максим Сергеевич"),
                (3, "admin", "admin", "Иванова Мария Павловна"),
            ]
            connection.executemany(
                "INSERT INTO users (role_id, login, password, full_name) VALUES (?, ?, ?, ?)",
                users,
            )

            categories = ["Столы", "Шкафы", "Кресла", "Тумбы"]
            manufacturers = ["ОфисЛайн", "МебельПроф", "Сибирь-Мебель"]
            suppliers = ["Склад Север", "Партнер Мебель", "Логистика НСК"]
            connection.executemany("INSERT INTO categories (name) VALUES (?)", [(name,) for name in categories])
            connection.executemany("INSERT INTO manufacturers (name) VALUES (?)", [(name,) for name in manufacturers])
            connection.executemany("INSERT INTO suppliers (name) VALUES (?)", [(name,) for name in suppliers])

            products = [
                ("DEMO-001", 1, 1, 1, "Стол письменный Лайт", "Рабочий стол для офиса с кабель-каналом", 8400.00, "шт", 12, 0, None),
                ("DEMO-002", 1, 2, 2, "Стол руководителя Премьер", "Расширенная столешница и боковая приставка", 22900.00, "шт", 4, 12, None),
                ("DEMO-003", 2, 3, 1, "Шкаф архивный закрытый", "Две секции, замок, регулируемые полки", 17900.00, "шт", 0, 5, None),
                ("DEMO-004", 3, 2, 3, "Кресло оператора Комфорт", "Сетчатая спинка, регулировка высоты", 6900.00, "шт", 18, 18, None),
                ("DEMO-005", 4, 1, 2, "Тумба мобильная 3 ящика", "Колесные опоры и центральный замок", 7600.00, "шт", 7, 9, None),
            ]
            connection.executemany(
                """
                INSERT INTO products
                    (article, category_id, manufacturer_id, supplier_id, name, description,
                     price, unit, stock_quantity, discount_percent, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                products,
            )

            connection.execute(
                "INSERT INTO orders (customer_name, created_date, status) VALUES (?, ?, ?)",
                ("ООО Бизнес Центр", "2026-06-19", "Новый"),
            )
            connection.executemany(
                "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
                [(1, 1, 3), (1, 4, 6)],
            )

    def migrate_image_paths(self):
        with self.connect() as connection:
            products = connection.execute(
                "SELECT id, image_path FROM products WHERE image_path IS NOT NULL"
            ).fetchall()
            for product in products:
                current = BASE_DIR / product["image_path"]
                if current.suffix.casefold() not in {".jpg", ".jpeg"}:
                    continue
                prepared = prepare_display_image(current)
                if prepared != product["image_path"]:
                    connection.execute(
                        "UPDATE products SET image_path = ? WHERE id = ?",
                        (prepared, product["id"]),
                    )

    def get_or_create(self, connection, table, name):
        existing = connection.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
        if existing:
            return existing["id"]
        cursor = connection.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
        return cursor.lastrowid

    def seed_imported_data(self, connection):
        role_names = {
            "Клиент": "client",
            "Менеджер": "manager",
            "Администратор": "admin",
        }
        for name, code in role_names.items():
            connection.execute("INSERT INTO roles (code, name) VALUES (?, ?)", (code, name))

        for user in row_dicts(USERS_IMPORT_PATH):
            role_name = str(user.get("Роль сотрудника") or "").strip()
            role_code = role_names.get(role_name, "client")
            role_id = connection.execute("SELECT id FROM roles WHERE code = ?", (role_code,)).fetchone()["id"]
            connection.execute(
                "INSERT INTO users (role_id, login, password, full_name) VALUES (?, ?, ?, ?)",
                (
                    role_id,
                    str(user.get("Логин") or "").strip(),
                    str(user.get("Пароль") or "").strip(),
                    str(user.get("ФИО") or "").strip(),
                ),
            )

        demo_users = [
            ("client", "client", "client", "Демо Клиент"),
            ("manager", "manager", "manager", "Демо Менеджер"),
            ("admin", "admin", "admin", "Администратор системы"),
        ]
        for role_code, login, password, full_name in demo_users:
            role_id = connection.execute("SELECT id FROM roles WHERE code = ?", (role_code,)).fetchone()["id"]
            connection.execute(
                "INSERT OR IGNORE INTO users (role_id, login, password, full_name) VALUES (?, ?, ?, ?)",
                (role_id, login, password, full_name),
            )

        article_to_id = {}
        for product in row_dicts(PRODUCTS_IMPORT_PATH):
            article = str(product.get("Артикул") or "").strip()
            if not article:
                continue
            category_id = self.get_or_create(connection, "categories", str(product.get("Категория товара") or "Без категории").strip())
            manufacturer_id = self.get_or_create(connection, "manufacturers", str(product.get("Производитель") or "Не указан").strip())
            supplier_id = self.get_or_create(connection, "suppliers", str(product.get("Поставщик") or "Не указан").strip())
            cursor = connection.execute(
                """
                INSERT INTO products
                    (article, category_id, manufacturer_id, supplier_id, name, description,
                     price, unit, stock_quantity, discount_percent, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article,
                    category_id,
                    manufacturer_id,
                    supplier_id,
                    str(product.get("Наименование товара") or "").strip(),
                    str(product.get("Описание товара") or "").strip(),
                    float(product.get("Цена") or 0),
                    str(product.get("Единица измерения") or "шт").strip(),
                    int(product.get("Кол-во на складе") or 0),
                    float(product.get("Действующая скидка") or 0),
                    find_asset_path(product.get("Фото")),
                ),
            )
            article_to_id[article] = cursor.lastrowid

        if ORDERS_IMPORT_PATH.exists():
            for order in row_dicts(ORDERS_IMPORT_PATH):
                order_id = int(order.get("Номер заказа") or 0)
                if order_id <= 0:
                    continue
                customer = str(order.get("ФИО авторизированного клиента") or "Покупатель").strip()
                status = str(order.get("Статус заказа") or "Новый").strip()
                created_date = str(order.get("Дата заказа") or "")
                connection.execute(
                    "INSERT OR IGNORE INTO orders (id, customer_name, created_date, status) VALUES (?, ?, ?, ?)",
                    (order_id, customer, created_date, status),
                )
                parts = [part.strip() for part in str(order.get("Артикул заказа") or "").split(",")]
                for index in range(0, len(parts) - 1, 2):
                    article = parts[index]
                    product_id = article_to_id.get(article)
                    if not product_id:
                        continue
                    try:
                        quantity = int(parts[index + 1])
                    except ValueError:
                        quantity = 1
                    connection.execute(
                        "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
                        (order_id, product_id, quantity),
                    )

    def authorize(self, login, password):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT u.id, u.full_name, r.code AS role_code, r.name AS role_name
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.login = ? AND u.password = ?
                """,
                (login, password),
            ).fetchone()

    def dictionaries(self):
        with self.connect() as connection:
            return {
                "categories": connection.execute("SELECT id, name FROM categories ORDER BY name").fetchall(),
                "manufacturers": connection.execute("SELECT id, name FROM manufacturers ORDER BY name").fetchall(),
                "suppliers": connection.execute("SELECT id, name FROM suppliers ORDER BY name").fetchall(),
            }

    def fetch_products(self, search="", discount_range=None, sort_mode="Без сортировки"):
        where = []
        params = []
        search = search.strip()
        if discount_range:
            start, end = discount_range
            if end is None:
                where.append("p.discount_percent >= ?")
                params.append(start)
            else:
                where.append("p.discount_percent BETWEEN ? AND ?")
                params.extend([start, end])

        order_by = "p.name ASC"
        if sort_mode == "Цена по возрастанию":
            order_by = "p.price ASC, p.name ASC"
        elif sort_mode == "Цена по убыванию":
            order_by = "p.price DESC, p.name ASC"
        elif sort_mode == "Остаток по возрастанию":
            order_by = "p.stock_quantity ASC, p.name ASC"
        elif sort_mode == "Остаток по убыванию":
            order_by = "p.stock_quantity DESC, p.name ASC"

        query = f"""
            SELECT
                p.id,
                p.article,
                p.name,
                p.description,
                p.price,
                p.unit,
                p.stock_quantity,
                p.discount_percent,
                p.image_path,
                c.name AS category_name,
                m.name AS manufacturer_name,
                s.name AS supplier_name
            FROM products p
            JOIN categories c ON c.id = p.category_id
            JOIN manufacturers m ON m.id = p.manufacturer_id
            JOIN suppliers s ON s.id = p.supplier_id
            {'WHERE ' + ' AND '.join(where) if where else ''}
            ORDER BY {order_by}
        """
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()

        if not search:
            return rows

        needle = search.casefold()
        return [
            row
            for row in rows
            if needle in " ".join(
                [
                    row["name"],
                    row["article"],
                    row["description"],
                    row["category_name"],
                    row["manufacturer_name"],
                    row["supplier_name"],
                    row["unit"],
                ]
            ).casefold()
        ]

    def fetch_product(self, product_id):
        with self.connect() as connection:
            return connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    def save_product(self, product_id, values):
        with self.connect() as connection:
            if product_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO products
                        (article, category_id, manufacturer_id, supplier_id, name, description,
                         price, unit, stock_quantity, discount_percent, image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                return cursor.lastrowid
            connection.execute(
                """
                UPDATE products
                SET article = ?, category_id = ?, manufacturer_id = ?, supplier_id = ?,
                    name = ?, description = ?, price = ?, unit = ?,
                    stock_quantity = ?, discount_percent = ?, image_path = ?
                WHERE id = ?
                """,
                (*values, product_id),
            )
            return product_id

    def product_in_orders(self, product_id):
        with self.connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM order_items WHERE product_id = ?",
                (product_id,),
            ).fetchone()[0] > 0

    def delete_product(self, product_id):
        if self.product_in_orders(product_id):
            raise ValueError("Товар присутствует в заказе, поэтому удалить его нельзя")
        product = self.fetch_product(product_id)
        with self.connect() as connection:
            connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
        if product and product["image_path"]:
            image_path = BASE_DIR / product["image_path"]
            if image_path.exists() and image_path.parent == IMAGES_DIR:
                image_path.unlink()


class LoginFrame(ttk.Frame):
    def __init__(self, app):
        super().__init__(app, padding=24, style="App.TFrame")
        self.app = app
        self.login_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.build_ui()

    def build_ui(self):
        self.columnconfigure(0, weight=1)
        card = ttk.Frame(self, padding=20, style="Panel.TFrame")
        card.grid(row=0, column=0)

        if self.app.logo_photo:
            ttk.Label(card, image=self.app.logo_photo, style="Panel.TLabel").grid(
                row=0,
                column=0,
                columnspan=2,
                pady=(0, 10),
            )
        else:
            tk.Label(
                card,
                text="Мебельный склад",
                bg=SECONDARY_BG,
                fg="black",
                font=TITLE_FONT,
            ).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(card, text="Вход в систему", font=SUBTITLE_FONT, style="Panel.TLabel").grid(row=1, column=0, columnspan=2, pady=(0, 18))
        ttk.Label(card, text="Логин", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(card, textvariable=self.login_var, width=28).grid(row=2, column=1, pady=4)
        ttk.Label(card, text="Пароль", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(card, textvariable=self.password_var, show="*", width=28).grid(row=3, column=1, pady=4)

        buttons = ttk.Frame(card, style="Panel.TFrame")
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        accent_button(buttons, "Войти", self.login).pack(side=tk.LEFT)
        plain_button(buttons, "Войти как гость", self.guest_login).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(
            card,
            text="Демо: client/client, manager/manager, admin/admin",
            foreground="#666666",
            style="Panel.TLabel",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def login(self):
        user = self.app.database.authorize(self.login_var.get().strip(), self.password_var.get())
        if not user:
            messagebox.showerror(
                "Ошибка авторизации",
                "Логин или пароль не найдены в базе данных. Проверьте ввод или войдите как гость.",
            )
            return
        self.app.show_products(dict(user))

    def guest_login(self):
        self.app.show_products(
            {
                "id": None,
                "full_name": "Гость",
                "role_code": "guest",
                "role_name": "Гость",
            }
        )


class ProductForm(tk.Toplevel):
    def __init__(self, parent, database: Database, product_id, on_saved):
        super().__init__(parent)
        self.database = database
        self.product_id = product_id
        self.on_saved = on_saved
        self.dicts = self.database.dictionaries()
        self.selected_image_path = None
        self.original_image_path = None

        self.title("Редактирование товара" if product_id else "Добавление товара")
        self.configure(bg=PRIMARY_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.category_var = tk.StringVar()
        self.manufacturer_var = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.article_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.description_text = None
        self.price_var = tk.StringVar(value="0")
        self.unit_var = tk.StringVar(value="шт")
        self.stock_var = tk.StringVar(value="0")
        self.discount_var = tk.StringVar(value="0")
        self.image_label_var = tk.StringVar(value="Изображение: заглушка")

        self.build_ui()
        self.load_defaults()
        if self.product_id:
            self.load_product()

    def build_ui(self):
        frame = ttk.Frame(self, padding=16, style="App.TFrame")
        frame.grid(sticky="nsew")

        row = 0
        if self.product_id:
            ttk.Label(frame, text=f"ID товара: {self.product_id}", style="App.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
            row += 1

        self.category_box = self.add_combo(frame, row, "Категория", self.category_var, "categories")
        row += 1
        self.add_entry(frame, row, "Артикул", self.article_var)
        row += 1
        self.add_entry(frame, row, "Наименование", self.name_var)
        row += 1

        ttk.Label(frame, text="Описание", style="App.TLabel").grid(row=row, column=0, sticky="nw", pady=4)
        self.description_text = tk.Text(frame, width=42, height=4, font=BASE_FONT, bg=PRIMARY_BG)
        self.description_text.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        self.manufacturer_box = self.add_combo(frame, row, "Производитель", self.manufacturer_var, "manufacturers")
        row += 1
        self.supplier_box = self.add_combo(frame, row, "Поставщик", self.supplier_var, "suppliers")
        row += 1
        self.add_entry(frame, row, "Цена", self.price_var)
        row += 1
        self.add_entry(frame, row, "Единица измерения", self.unit_var)
        row += 1
        self.add_entry(frame, row, "Количество на складе", self.stock_var)
        row += 1
        self.add_entry(frame, row, "Действующая скидка, %", self.discount_var)
        row += 1

        ttk.Label(frame, textvariable=self.image_label_var, style="App.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 2))
        row += 1
        plain_button(frame, "Выбрать изображение", self.choose_image).grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(14, 0))
        accent_button(buttons, "Сохранить", self.save).pack(side=tk.LEFT)
        plain_button(buttons, "Отмена", self.destroy).pack(side=tk.LEFT, padx=(8, 0))

    def add_entry(self, frame, row, label, variable):
        ttk.Label(frame, text=label, style="App.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=variable, width=44).grid(row=row, column=1, sticky="ew", pady=4)

    def add_combo(self, frame, row, label, variable, key):
        ttk.Label(frame, text=label, style="App.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        combo = ttk.Combobox(frame, textvariable=variable, state="readonly", width=41)
        combo["values"] = [item["name"] for item in self.dicts[key]]
        combo.grid(row=row, column=1, sticky="ew", pady=4)
        return combo

    def load_defaults(self):
        for combo in (self.category_box, self.manufacturer_box, self.supplier_box):
            if combo["values"]:
                combo.current(0)

    def load_product(self):
        product = self.database.fetch_product(self.product_id)
        if not product:
            messagebox.showerror("Ошибка", "Товар не найден")
            self.destroy()
            return

        self.set_combo_by_id(self.category_box, self.dicts["categories"], product["category_id"])
        self.set_combo_by_id(self.manufacturer_box, self.dicts["manufacturers"], product["manufacturer_id"])
        self.set_combo_by_id(self.supplier_box, self.dicts["suppliers"], product["supplier_id"])
        self.article_var.set(product["article"])
        self.name_var.set(product["name"])
        self.description_text.insert("1.0", product["description"])
        self.price_var.set(f"{product['price']:.2f}")
        self.unit_var.set(product["unit"])
        self.stock_var.set(str(product["stock_quantity"]))
        self.discount_var.set(f"{product['discount_percent']:.2f}")
        self.original_image_path = product["image_path"]
        if product["image_path"]:
            self.image_label_var.set(f"Изображение: {product['image_path']}")

    def set_combo_by_id(self, combo, rows, row_id):
        index = next((i for i, row in enumerate(rows) if row["id"] == row_id), 0)
        combo.current(index)

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("PNG изображения", "*.png"), ("GIF изображения", "*.gif"), ("Все файлы", "*.*")],
        )
        if not path:
            return

        try:
            width, height = image_dimensions(path)
        except (OSError, tk.TclError, struct.error):
            messagebox.showerror("Ошибка изображения", "Выбранный файл не удалось открыть как изображение.")
            return

        if width > 300 or height > 200:
            messagebox.showerror(
                "Ошибка изображения",
                "Размер изображения должен быть не больше 300x200 пикселей.",
            )
            return

        self.selected_image_path = Path(path)
        self.image_label_var.set(f"Изображение: {self.selected_image_path.name}")

    def validate(self):
        errors = []
        if not self.article_var.get().strip():
            errors.append("Введите артикул товара")
        if not self.name_var.get().strip():
            errors.append("Введите наименование товара")
        if not self.description_text.get("1.0", "end").strip():
            errors.append("Введите описание товара")
        if not self.unit_var.get().strip():
            errors.append("Введите единицу измерения")

        try:
            price = float(self.price_var.get())
            if price < 0:
                errors.append("Стоимость товара не может быть отрицательной")
        except ValueError:
            errors.append("Стоимость товара должна быть числом")

        try:
            stock = int(self.stock_var.get())
            if stock < 0:
                errors.append("Количество на складе не может быть отрицательным")
        except ValueError:
            errors.append("Количество на складе должно быть целым числом")

        try:
            discount = float(self.discount_var.get())
            if discount < 0:
                errors.append("Скидка не может быть отрицательной")
        except ValueError:
            errors.append("Скидка должна быть числом")

        return errors

    def save_image_if_needed(self, product_id):
        if not self.selected_image_path:
            return self.original_image_path

        extension = self.selected_image_path.suffix.lower() or ".png"
        target = IMAGES_DIR / f"product_{product_id}{extension}"
        shutil.copy2(self.selected_image_path, target)

        if self.original_image_path:
            old_path = BASE_DIR / self.original_image_path
            if old_path.exists() and old_path != target and old_path.parent == IMAGES_DIR:
                old_path.unlink()

        return str(target.relative_to(BASE_DIR))

    def save(self):
        errors = self.validate()
        if errors:
            messagebox.showerror("Ошибка валидации", "\n".join(errors))
            return

        values_without_image = (
            self.article_var.get().strip(),
            self.dicts["categories"][self.category_box.current()]["id"],
            self.dicts["manufacturers"][self.manufacturer_box.current()]["id"],
            self.dicts["suppliers"][self.supplier_box.current()]["id"],
            self.name_var.get().strip(),
            self.description_text.get("1.0", "end").strip(),
            float(self.price_var.get()),
            self.unit_var.get().strip(),
            int(self.stock_var.get()),
            float(self.discount_var.get()),
        )

        try:
            product_id = self.product_id or self.database.save_product(None, (*values_without_image, None))
            image_path = self.save_image_if_needed(product_id)
            self.database.save_product(product_id, (*values_without_image, image_path))
        except (sqlite3.Error, OSError) as exc:
            messagebox.showerror("Ошибка сохранения", str(exc))
            return

        self.on_saved()
        self.destroy()


class ProductFrame(ttk.Frame):
    def __init__(self, app, user):
        super().__init__(app, style="App.TFrame")
        self.app = app
        self.user = user
        self.search_var = tk.StringVar()
        self.discount_var = tk.StringVar(value="Все диапазоны")
        self.sort_var = tk.StringVar(value="Без сортировки")
        self.images = {}
        self.edit_window = None

        self.build_ui()
        self.reload_products()

    def build_ui(self):
        header = ttk.Frame(self, padding=(12, 12, 12, 8), style="Panel.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text="Список товаров", font=SUBTITLE_FONT, style="Panel.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text=f"{self.user['full_name']} ({self.user['role_name']})", style="Panel.TLabel").pack(side=tk.RIGHT)
        plain_button(header, "Выйти", self.app.show_login).pack(side=tk.RIGHT, padx=(0, 12))

        controls = ttk.Frame(self, padding=(12, 8, 12, 8), style="App.TFrame")
        controls.pack(fill=tk.X)

        role = self.user["role_code"]
        can_search = role in {"manager", "admin"}
        can_edit = role == "admin"

        if can_search:
            ttk.Label(controls, text="Поиск", style="App.TLabel").pack(side=tk.LEFT)
            search_entry = ttk.Entry(controls, textvariable=self.search_var, width=26)
            search_entry.pack(side=tk.LEFT, padx=(6, 12))
            search_entry.bind("<KeyRelease>", lambda _event: self.reload_products())

            ttk.Label(controls, text="Скидка", style="App.TLabel").pack(side=tk.LEFT)
            discount_box = ttk.Combobox(
                controls,
                textvariable=self.discount_var,
                values=tuple(DISCOUNT_RANGES.keys()),
                state="readonly",
                width=18,
            )
            discount_box.pack(side=tk.LEFT, padx=(6, 12))
            discount_box.bind("<<ComboboxSelected>>", lambda _event: self.reload_products())

            ttk.Label(controls, text="Сортировка", style="App.TLabel").pack(side=tk.LEFT)
            sort_box = ttk.Combobox(
                controls,
                textvariable=self.sort_var,
                values=(
                    "Без сортировки",
                    "Цена по возрастанию",
                    "Цена по убыванию",
                    "Остаток по возрастанию",
                    "Остаток по убыванию",
                ),
                state="readonly",
                width=24,
            )
            sort_box.pack(side=tk.LEFT, padx=(6, 12))
            sort_box.bind("<<ComboboxSelected>>", lambda _event: self.reload_products())

        if can_edit:
            accent_button(controls, "Добавить товар", self.open_create_form).pack(side=tk.RIGHT)
            plain_button(controls, "Удалить товар", self.delete_selected).pack(side=tk.RIGHT, padx=(0, 8))
            plain_button(controls, "Редактировать", self.open_edit_form).pack(side=tk.RIGHT, padx=(0, 8))

        columns = ("article", "category", "description", "manufacturer", "supplier", "price", "unit", "stock", "discount")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", height=16)
        self.tree.heading("#0", text="Фото / товар")
        self.tree.column("#0", width=210, anchor="w")
        headings = {
            "category": "Категория",
            "article": "Артикул",
            "description": "Описание",
            "manufacturer": "Производитель",
            "supplier": "Поставщик",
            "price": "Цена",
            "unit": "Ед.",
            "stock": "Остаток",
            "discount": "Скидка",
        }
        widths = {
            "category": 120,
            "article": 90,
            "description": 250,
            "manufacturer": 130,
            "supplier": 130,
            "price": 135,
            "unit": 55,
            "stock": 75,
            "discount": 75,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            anchor = "e" if column in {"price", "stock", "discount"} else "w"
            self.tree.column(column, width=widths[column], anchor=anchor)

        self.tree.tag_configure("discount", background=DISCOUNT_BG, foreground="white")
        self.tree.tag_configure("empty_stock", background="#d9d9d9", foreground="#444444")
        self.tree.tag_configure("reduced_price", foreground="#b00020")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        if can_edit:
            self.tree.bind("<Double-1>", lambda _event: self.open_edit_form())

        self.summary_label = ttk.Label(self, padding=(12, 0, 12, 12), style="App.TLabel")
        self.summary_label.pack(fill=tk.X)

    def image_for_product(self, row):
        image_path = BASE_DIR / row["image_path"] if row["image_path"] else PLACEHOLDER_PATH
        if not image_path.exists():
            image_path = PLACEHOLDER_PATH

        key = str(image_path)
        if key in self.images:
            return self.images[key]

        if image_path == PLACEHOLDER_PATH:
            image = self.create_placeholder_photo()
        else:
            image = load_photo(image_path, 80, 60)
            if image is None:
                image = self.create_placeholder_photo()

        while image.width() > 80 or image.height() > 60:
            image = image.subsample(2, 2)
        self.images[key] = image
        return image

    def create_placeholder_photo(self):
        image = tk.PhotoImage(width=80, height=60)
        image.put("#f6f8fa", to=(0, 0, 80, 60))
        image.put("#d0d7de", to=(0, 0, 80, 12))
        image.put("#afb8c1", to=(24, 20, 56, 40))
        image.put("#ffffff", to=(28, 24, 52, 36))
        return image

    def reload_products(self):
        self.tree.delete(*self.tree.get_children())
        self.images.clear()
        role = self.user["role_code"]
        can_filter = role in {"manager", "admin"}
        discount_range = DISCOUNT_RANGES[self.discount_var.get()] if can_filter else None
        sort_mode = self.sort_var.get() if can_filter else "Без сортировки"
        search = self.search_var.get() if can_filter else ""

        rows = self.app.database.fetch_products(search, discount_range, sort_mode)
        for row in rows:
            tags = []
            if row["stock_quantity"] == 0:
                tags.append("empty_stock")
            elif row["discount_percent"] >= 15:
                tags.append("discount")
            elif row["discount_percent"] > 0:
                tags.append("reduced_price")

            self.tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                text=row["name"],
                image=self.image_for_product(row),
                values=(
                    row["article"],
                    row["category_name"],
                    row["description"],
                    row["manufacturer_name"],
                    row["supplier_name"],
                    price_text(row["price"], row["discount_percent"]),
                    row["unit"],
                    row["stock_quantity"],
                    f"{row['discount_percent']:.2f}%",
                ),
                tags=tuple(tags),
            )
        self.summary_label.config(text=f"Показано товаров: {len(rows)}")

    def selected_product_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Выбор товара", "Выберите товар в списке.")
            return None
        return int(selected[0])

    def open_create_form(self):
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.focus()
            return
        self.edit_window = ProductForm(self, self.app.database, None, self.reload_products)

    def open_edit_form(self):
        product_id = self.selected_product_id()
        if product_id is None:
            return
        if self.edit_window and self.edit_window.winfo_exists():
            self.edit_window.focus()
            return
        self.edit_window = ProductForm(self, self.app.database, product_id, self.reload_products)

    def delete_selected(self):
        product_id = self.selected_product_id()
        if product_id is None:
            return
        if not messagebox.askyesno("Удаление товара", f"Удалить товар №{product_id}? Операцию нельзя отменить."):
            return
        try:
            self.app.database.delete_product(product_id)
        except (sqlite3.Error, ValueError) as exc:
            messagebox.showerror("Ошибка удаления", str(exc))
            return
        self.reload_products()


class FurnitureStoreApp(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_directories()
        self.configure(bg=PRIMARY_BG)
        self.configure_styles()
        self.logo_photo = load_photo(LOGO_PATH, 220, 120)
        self.app_icon_photo = load_photo(APP_ICON_PATH, 64, 64)
        if self.app_icon_photo:
            self.iconphoto(True, self.app_icon_photo)
        self.database = Database(DB_PATH)
        self.title("Вариант 5 2026 - мебельный магазин")
        self.geometry("1180x680")
        self.minsize(980, 560)
        self.current_frame = None
        self.show_login()

    def configure_styles(self):
        self.option_add("*Font", BASE_FONT)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=BASE_FONT)
        style.configure("App.TFrame", background=PRIMARY_BG)
        style.configure("Panel.TFrame", background=SECONDARY_BG)
        style.configure("App.TLabel", background=PRIMARY_BG, foreground="black", font=BASE_FONT)
        style.configure("Panel.TLabel", background=SECONDARY_BG, foreground="black", font=BASE_FONT)
        style.configure("TEntry", fieldbackground=PRIMARY_BG, font=BASE_FONT)
        style.configure("TCombobox", fieldbackground=PRIMARY_BG, font=BASE_FONT)
        style.configure("Treeview", background=PRIMARY_BG, fieldbackground=PRIMARY_BG, foreground="black", font=BASE_FONT)
        style.configure("Treeview.Heading", background=SECONDARY_BG, foreground="black", font=BUTTON_FONT)
        style.map("Treeview", background=[("selected", ACCENT_BG)], foreground=[("selected", "white")])

    def set_frame(self, frame):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_login(self):
        self.title("Вход в систему")
        self.set_frame(LoginFrame(self))

    def show_products(self, user):
        self.title(f"Список товаров - {user['role_name']}")
        self.set_frame(ProductFrame(self, user))


if __name__ == "__main__":
    app = FurnitureStoreApp()
    app.mainloop()
