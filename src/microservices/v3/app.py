import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "orders.db"
STATUSES = ("Новая", "В работе", "Согласована", "Выполнена", "Отменена")


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.init_schema()
        self.seed_demo_data()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self):
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS partner_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS partners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type_id INTEGER NOT NULL REFERENCES partner_types(id),
                    name TEXT NOT NULL,
                    director_name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 0),
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL CHECK (price >= 0)
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    partner_id INTEGER NOT NULL REFERENCES partners(id),
                    created_date TEXT NOT NULL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS order_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    price REAL NOT NULL CHECK (price >= 0)
                );
                """
            )

    def seed_demo_data(self):
        with self.connect() as connection:
            exists = connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0]
            if exists:
                return

            partner_types = ["Оптовый покупатель", "Розничная сеть", "Дистрибьютор"]
            connection.executemany(
                "INSERT INTO partner_types (name) VALUES (?)",
                [(name,) for name in partner_types],
            )

            partners = [
                (1, "ООО Альфа-Маркет", "Иванов Сергей Петрович", "Новосибирск, Красный проспект, 25", 8, "+7 383 200-10-10", "alpha@example.ru"),
                (2, "ТД Сибирь", "Петрова Анна Игоревна", "Новосибирск, ул. Ленина, 11", 6, "+7 383 222-20-20", "sibir@example.ru"),
                (3, "ИП Кузнецов", "Кузнецов Павел Олегович", "Бердск, ул. Лунная, 4", 9, "+7 913 000-11-22", "kuznetsov@example.ru"),
            ]
            connection.executemany(
                """
                INSERT INTO partners
                    (type_id, name, director_name, address, rating, phone, email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                partners,
            )

            products = [
                ("Корпус датчика", 1450.00),
                ("Контроллер управления", 3200.00),
                ("Кабельный комплект", 890.00),
                ("Монтажный набор", 560.00),
            ]
            connection.executemany(
                "INSERT INTO products (name, price) VALUES (?, ?)",
                products,
            )

            orders = [
                (1, "2026-06-01", "Новая"),
                (2, "2026-06-05", "В работе"),
                (3, "2026-06-11", "Выполнена"),
            ]
            connection.executemany(
                "INSERT INTO orders (partner_id, created_date, status) VALUES (?, ?, ?)",
                orders,
            )

            order_products = [
                (1, 1, 4, 1450.00),
                (1, 3, 2, 890.00),
                (2, 2, 1, 3200.00),
                (2, 4, 8, 560.00),
                (3, 1, 2, 1450.00),
                (3, 2, 2, 3200.00),
            ]
            connection.executemany(
                """
                INSERT INTO order_products (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
                """,
                order_products,
            )

    def fetch_orders(self, search="", status="Все"):
        query = """
            SELECT
                o.id,
                p.name AS partner,
                o.created_date,
                o.status,
                COALESCE(SUM(op.quantity * op.price), 0) AS total
            FROM orders o
            JOIN partners p ON p.id = o.partner_id
            LEFT JOIN order_products op ON op.order_id = o.id
            WHERE (? = '' OR lower(p.name) LIKE lower(?))
              AND (? = 'Все' OR o.status = ?)
            GROUP BY o.id, p.name, o.created_date, o.status
            ORDER BY o.created_date DESC, o.id DESC
        """
        like = f"%{search.strip()}%"
        with self.connect() as connection:
            return connection.execute(query, (search.strip(), like, status, status)).fetchall()

    def fetch_order(self, order_id):
        with self.connect() as connection:
            order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            products = connection.execute(
                """
                SELECT op.product_id, pr.name, op.quantity, op.price
                FROM order_products op
                JOIN products pr ON pr.id = op.product_id
                WHERE op.order_id = ?
                ORDER BY op.id
                """,
                (order_id,),
            ).fetchall()
            return order, products

    def fetch_partners(self):
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT p.id, pt.name || ' - ' || p.name AS title
                FROM partners p
                JOIN partner_types pt ON pt.id = p.type_id
                ORDER BY p.name
                """
            ).fetchall()

    def fetch_products(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT id, name, price FROM products ORDER BY name"
            ).fetchall()

    def save_order(self, order_id, partner_id, created_date, status, items):
        with self.connect() as connection:
            if order_id is None:
                cursor = connection.execute(
                    "INSERT INTO orders (partner_id, created_date, status) VALUES (?, ?, ?)",
                    (partner_id, created_date, status),
                )
                order_id = cursor.lastrowid
            else:
                connection.execute(
                    """
                    UPDATE orders
                    SET partner_id = ?, created_date = ?, status = ?
                    WHERE id = ?
                    """,
                    (partner_id, created_date, status, order_id),
                )
                connection.execute("DELETE FROM order_products WHERE order_id = ?", (order_id,))

            connection.executemany(
                """
                INSERT INTO order_products (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
                """,
                [(order_id, product_id, quantity, price) for product_id, quantity, price in items],
            )

    def delete_order(self, order_id):
        with self.connect() as connection:
            connection.execute("DELETE FROM orders WHERE id = ?", (order_id,))


class OrderForm(tk.Toplevel):
    def __init__(self, parent, database: Database, on_saved, order_id=None):
        super().__init__(parent)
        self.database = database
        self.on_saved = on_saved
        self.order_id = order_id
        self.partners = self.database.fetch_partners()
        self.products = self.database.fetch_products()
        self.items = []

        self.title("Редактирование заявки" if order_id else "Новая заявка")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.partner_var = tk.StringVar()
        self.date_var = tk.StringVar(value="2026-06-19")
        self.status_var = tk.StringVar(value=STATUSES[0])
        self.product_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")

        self.build_ui()
        self.load_defaults()
        if self.order_id:
            self.load_order()

    def build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.grid(sticky="nsew")

        ttk.Label(root, text="Партнер").grid(row=0, column=0, sticky="w", pady=4)
        self.partner_box = ttk.Combobox(root, textvariable=self.partner_var, width=42, state="readonly")
        self.partner_box.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4)

        ttk.Label(root, text="Дата").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(root, textvariable=self.date_var, width=18).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(root, text="Статус").grid(row=1, column=2, sticky="w", padx=(14, 4), pady=4)
        ttk.Combobox(root, textvariable=self.status_var, values=STATUSES, state="readonly", width=18).grid(row=1, column=3, sticky="w", pady=4)

        ttk.Separator(root).grid(row=2, column=0, columnspan=4, sticky="ew", pady=10)

        ttk.Label(root, text="Товар").grid(row=3, column=0, sticky="w", pady=4)
        self.product_box = ttk.Combobox(root, textvariable=self.product_var, width=30, state="readonly")
        self.product_box.grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(root, text="Кол-во").grid(row=3, column=2, sticky="w", padx=(14, 4), pady=4)
        ttk.Entry(root, textvariable=self.quantity_var, width=8).grid(row=3, column=3, sticky="w", pady=4)

        ttk.Button(root, text="Добавить товар", command=self.add_item).grid(row=4, column=1, sticky="w", pady=6)
        ttk.Button(root, text="Удалить товар", command=self.remove_item).grid(row=4, column=2, columnspan=2, sticky="w", pady=6)

        columns = ("product", "quantity", "price", "total")
        self.items_tree = ttk.Treeview(root, columns=columns, show="headings", height=7)
        self.items_tree.heading("product", text="Товар")
        self.items_tree.heading("quantity", text="Кол-во")
        self.items_tree.heading("price", text="Цена")
        self.items_tree.heading("total", text="Сумма")
        self.items_tree.column("product", width=240)
        self.items_tree.column("quantity", width=70, anchor="center")
        self.items_tree.column("price", width=90, anchor="e")
        self.items_tree.column("total", width=100, anchor="e")
        self.items_tree.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=8)

        self.total_label = ttk.Label(root, text="Итого: 0.00 руб.")
        self.total_label.grid(row=6, column=0, columnspan=4, sticky="e", pady=(0, 12))

        ttk.Button(root, text="Сохранить", command=self.save).grid(row=7, column=2, sticky="e")
        ttk.Button(root, text="Отмена", command=self.destroy).grid(row=7, column=3, sticky="e", padx=(8, 0))

    def load_defaults(self):
        self.partner_box["values"] = [row["title"] for row in self.partners]
        self.product_box["values"] = [row["name"] for row in self.products]
        if self.partners:
            self.partner_box.current(0)
        if self.products:
            self.product_box.current(0)

    def load_order(self):
        order, products = self.database.fetch_order(self.order_id)
        if not order:
            messagebox.showerror("Ошибка", "Заявка не найдена")
            self.destroy()
            return

        partner_index = next(
            (i for i, partner in enumerate(self.partners) if partner["id"] == order["partner_id"]),
            0,
        )
        self.partner_box.current(partner_index)
        self.date_var.set(order["created_date"])
        self.status_var.set(order["status"])
        self.items = [
            (row["product_id"], row["name"], row["quantity"], row["price"])
            for row in products
        ]
        self.refresh_items()

    def add_item(self):
        product_index = self.product_box.current()
        if product_index < 0:
            messagebox.showerror("Ошибка", "Выберите товар")
            return

        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Количество должно быть целым числом больше нуля")
            return

        product = self.products[product_index]
        self.items.append((product["id"], product["name"], quantity, float(product["price"])))
        self.refresh_items()

    def remove_item(self):
        selected = self.items_tree.selection()
        if not selected:
            return
        index = self.items_tree.index(selected[0])
        del self.items[index]
        self.refresh_items()

    def refresh_items(self):
        self.items_tree.delete(*self.items_tree.get_children())
        total = 0
        for product_id, name, quantity, price in self.items:
            line_total = quantity * price
            total += line_total
            self.items_tree.insert(
                "",
                tk.END,
                values=(name, quantity, f"{price:.2f}", f"{line_total:.2f}"),
            )
        self.total_label.config(text=f"Итого: {total:.2f} руб.")

    def validate(self):
        if self.partner_box.current() < 0:
            return "Выберите партнера"
        if not self.date_var.get().strip():
            return "Введите дату заявки"
        if self.status_var.get() not in STATUSES:
            return "Выберите корректный статус"
        if not self.items:
            return "Добавьте хотя бы один товар"
        return None

    def save(self):
        error = self.validate()
        if error:
            messagebox.showerror("Ошибка валидации", error)
            return

        partner_id = self.partners[self.partner_box.current()]["id"]
        items = [(product_id, quantity, price) for product_id, _name, quantity, price in self.items]
        try:
            self.database.save_order(
                self.order_id,
                partner_id,
                self.date_var.get().strip(),
                self.status_var.get(),
                items,
            )
        except sqlite3.Error as exc:
            messagebox.showerror("Ошибка БД", str(exc))
            return

        self.on_saved()
        self.destroy()


class OrderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.database = Database(DB_PATH)
        self.search_var = tk.StringVar()
        self.status_filter_var = tk.StringVar(value="Все")

        self.title("Вариант 3 - заявки партнеров")
        self.geometry("900x560")
        self.minsize(760, 430)

        self.build_ui()
        self.load_orders()

    def build_ui(self):
        toolbar = ttk.Frame(self, padding=(12, 12, 12, 6))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Поиск").pack(side=tk.LEFT)
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=28)
        search_entry.pack(side=tk.LEFT, padx=(6, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.load_orders())

        ttk.Label(toolbar, text="Статус").pack(side=tk.LEFT)
        status_box = ttk.Combobox(
            toolbar,
            textvariable=self.status_filter_var,
            values=("Все",) + STATUSES,
            state="readonly",
            width=16,
        )
        status_box.pack(side=tk.LEFT, padx=(6, 12))
        status_box.bind("<<ComboboxSelected>>", lambda _event: self.load_orders())

        ttk.Button(toolbar, text="Обновить", command=self.load_orders).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Новая заявка", command=self.open_create_form).pack(side=tk.RIGHT)

        columns = ("id", "partner", "date", "total", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.heading("id", text="№")
        self.tree.heading("partner", text="Партнер")
        self.tree.heading("date", text="Дата")
        self.tree.heading("total", text="Сумма")
        self.tree.heading("status", text="Статус")
        self.tree.column("id", width=70, anchor="center")
        self.tree.column("partner", width=300)
        self.tree.column("date", width=120, anchor="center")
        self.tree.column("total", width=130, anchor="e")
        self.tree.column("status", width=140, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda _event: self.open_edit_form())

        bottom = ttk.Frame(self, padding=(12, 0, 12, 12))
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="Редактировать", command=self.open_edit_form).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Удалить", command=self.delete_selected).pack(side=tk.LEFT, padx=(8, 0))
        self.summary_label = ttk.Label(bottom, text="")
        self.summary_label.pack(side=tk.RIGHT)

    def load_orders(self):
        self.tree.delete(*self.tree.get_children())
        rows = self.database.fetch_orders(
            self.search_var.get(),
            self.status_filter_var.get(),
        )
        total_sum = 0
        for row in rows:
            total_sum += row["total"]
            self.tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row["partner"],
                    row["created_date"],
                    f"{row['total']:.2f}",
                    row["status"],
                ),
            )
        self.summary_label.config(text=f"Заявок: {len(rows)} | Общая сумма: {total_sum:.2f} руб.")

    def selected_order_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Выбор заявки", "Выберите заявку в списке")
            return None
        return int(selected[0])

    def open_create_form(self):
        OrderForm(self, self.database, self.load_orders)

    def open_edit_form(self):
        order_id = self.selected_order_id()
        if order_id is not None:
            OrderForm(self, self.database, self.load_orders, order_id)

    def delete_selected(self):
        order_id = self.selected_order_id()
        if order_id is None:
            return
        if not messagebox.askyesno("Удаление", f"Удалить заявку №{order_id}?"):
            return
        try:
            self.database.delete_order(order_id)
        except sqlite3.Error as exc:
            messagebox.showerror("Ошибка БД", str(exc))
            return
        self.load_orders()


if __name__ == "__main__":
    app = OrderApp()
    app.mainloop()
