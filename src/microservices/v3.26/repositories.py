from __future__ import annotations

import sqlite3
from pathlib import Path

from database import BASE_DIR, connect


SORT_FIELDS = {
    "Без сортировки": None,
    "Количество": "stock_quantity",
    "Цена": "price",
    "Скидка": "discount",
}


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


def get_product(article: str) -> sqlite3.Row | None:
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
        category_id = _get_or_create(connection, "categories", str(product["category"]))
        manufacturer_id = _get_or_create(connection, "manufacturers", str(product["manufacturer"]))
        supplier_id = _get_or_create(connection, "suppliers", str(product["supplier"]))
        unit_id = _get_or_create(connection, "units", str(product["unit"]))

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


def _get_or_create(connection: sqlite3.Connection, table: str, name: str) -> int:
    clean_name = name.strip() or "Не указано"
    row = connection.execute(f"SELECT id FROM {table} WHERE name = ?", (clean_name,)).fetchone()
    if row:
        return int(row["id"])
    cursor = connection.execute(f"INSERT INTO {table} (name) VALUES (?)", (clean_name,))
    return int(cursor.lastrowid)


def _delete_managed_image(image_path: str | None) -> None:
    if not image_path or not image_path.startswith("app_assets/product_images/"):
        return
    path = BASE_DIR / image_path
    if path.exists():
        path.unlink()
