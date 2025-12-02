import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "warehouse.db"


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
                CREATE TABLE IF NOT EXISTS material_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type_id INTEGER NOT NULL REFERENCES material_types(id),
                    name TEXT NOT NULL,
                    price REAL NOT NULL CHECK (price >= 0),
                    unit TEXT NOT NULL,
                    pack_quantity INTEGER NOT NULL CHECK (pack_quantity > 0),
                    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
                    min_quantity INTEGER NOT NULL CHECK (min_quantity >= 0)
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    coefficient REAL NOT NULL CHECK (coefficient > 0),
                    loss_percent REAL NOT NULL CHECK (loss_percent >= 0)
                );

                CREATE TABLE IF NOT EXISTS product_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    material_id INTEGER NOT NULL REFERENCES materials(id),
                    quantity_required INTEGER NOT NULL CHECK (quantity_required > 0)
                );
                """
            )

    def seed_demo_data(self):
        with self.connect() as connection:
            exists = connection.execute("SELECT COUNT(*) FROM materials").fetchone()[0]
            if exists:
                return

            material_types = [
                "Листовой материал",
                "Фурнитура",
                "Кромочный материал",
                "Лакокрасочные материалы",
            ]
            connection.executemany(
                "INSERT INTO material_types (name) VALUES (?)",
                [(name,) for name in material_types],
            )

            materials = [
                (1, "ЛДСП 16 мм Дуб", 2450.00, "лист", 1, 38, 20),
                (1, "МДФ фасадный 18 мм", 3180.00, "лист", 1, 14, 12),
                (2, "Петля мебельная с доводчиком", 95.00, "шт", 100, 240, 150),
                (2, "Направляющая шариковая 450 мм", 260.00, "компл", 20, 46, 40),
                (3, "Кромка ПВХ 2 мм", 18.50, "м", 200, 780, 500),
                (4, "Лак матовый", 690.00, "л", 5, 24, 15),
            ]
            connection.executemany(
                """
                INSERT INTO materials
                    (type_id, name, price, unit, pack_quantity, stock_quantity, min_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                materials,
            )

            products = [
                ("Стол письменный", 1.25, 3.0),
                ("Шкаф офисный", 2.40, 5.0),
                ("Тумба мобильная", 0.90, 2.0),
            ]
            connection.executemany(
                "INSERT INTO products (name, coefficient, loss_percent) VALUES (?, ?, ?)",
                products,
            )

            product_materials = [
                (1, 1, 2),
                (1, 3, 4),
                (1, 5, 12),
                (2, 1, 4),
                (2, 2, 2),
                (2, 3, 8),
                (2, 4, 2),
                (2, 5, 24),
                (3, 1, 1),
                (3, 3, 6),
                (3, 4, 1),
            ]
            connection.executemany(
                """
                INSERT INTO product_materials (product_id, material_id, quantity_required)
                VALUES (?, ?, ?)
                """,
                product_materials,
            )

    def fetch_material_types(self):
        with self.connect() as connection:
            return connection.execute("SELECT id, name FROM material_types ORDER BY name").fetchall()

    def fetch_materials(self, search="", only_shortage=False):
        where = ["(? = '' OR lower(m.name) LIKE lower(?))"]
        params = [search.strip(), f"%{search.strip()}%"]
        if only_shortage:
            where.append("m.stock_quantity < m.min_quantity")

        query = f"""
            SELECT
                m.id,
                mt.name AS type_name,
                m.name,
                m.price,
                m.unit,
                m.pack_quantity,
                m.stock_quantity,
                m.min_quantity,
                COALESCE(SUM(pm.quantity_required), 0) AS required_total
            FROM materials m
            JOIN material_types mt ON mt.id = m.type_id
            LEFT JOIN product_materials pm ON pm.material_id = m.id
            WHERE {' AND '.join(where)}
            GROUP BY
                m.id, mt.name, m.name, m.price, m.unit,
                m.pack_quantity, m.stock_quantity, m.min_quantity
            ORDER BY m.name
        """
        with self.connect() as connection:
            return connection.execute(query, params).fetchall()

    def fetch_material(self, material_id):
        with self.connect() as connection:
            return connection.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()

    def fetch_products(self):
        with self.connect() as connection:
            return connection.execute(
                "SELECT id, name, coefficient, loss_percent FROM products ORDER BY name"
            ).fetchall()

    def save_material(self, material_id, values):
        with self.connect() as connection:
            if material_id is None:
                connection.execute(
                    """
                    INSERT INTO materials
                        (type_id, name, price, unit, pack_quantity, stock_quantity, min_quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            else:
                connection.execute(
                    """
                    UPDATE materials
                    SET type_id = ?, name = ?, price = ?, unit = ?,
                        pack_quantity = ?, stock_quantity = ?, min_quantity = ?
                    WHERE id = ?
                    """,
                    (*values, material_id),
                )

    def delete_material(self, material_id):
        with self.connect() as connection:
            used = connection.execute(
                "SELECT COUNT(*) FROM product_materials WHERE material_id = ?",
                (material_id,),
            ).fetchone()[0]
            if used:
                raise ValueError("Материал используется в продукции и не может быть удален")
            connection.execute("DELETE FROM materials WHERE id = ?", (material_id,))

    def calculate_product_count(self, product_id, material_id, stock, param1, param2):
        if product_id <= 0 or material_id <= 0 or stock < 0 or param1 <= 0 or param2 <= 0:
            return -1

        with self.connect() as connection:
            product = connection.execute(
                "SELECT coefficient, loss_percent FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
            material = connection.execute(
                "SELECT id FROM materials WHERE id = ?",
                (material_id,),
            ).fetchone()

        if not product or not material:
            return -1

        required_material = param1 * param2 * product["coefficient"] * (1 + product["loss_percent"] / 100)
        if required_material <= 0:
            return -1
        return int(stock // required_material)


class MaterialForm(tk.Toplevel):
    def __init__(self, parent, database: Database, on_saved, material_id=None):
        super().__init__(parent)
        self.database = database
        self.on_saved = on_saved
        self.material_id = material_id
        self.types = self.database.fetch_material_types()

        self.title("Редактирование материала" if material_id else "Новый материал")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.type_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.unit_var = tk.StringVar(value="шт")
        self.pack_var = tk.StringVar(value="1")
        self.stock_var = tk.StringVar(value="0")
        self.min_var = tk.StringVar(value="0")

        self.build_ui()
        if self.types:
            self.type_box.current(0)
        if self.material_id:
            self.load_material()

    def build_ui(self):
        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")

        fields = [
            ("Тип материала", "type"),
            ("Наименование", self.name_var),
            ("Цена", self.price_var),
            ("Единица", self.unit_var),
            ("В упаковке", self.pack_var),
            ("Остаток", self.stock_var),
            ("Минимум", self.min_var),
        ]

        for row, (label, variable) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            if variable == "type":
                self.type_box = ttk.Combobox(
                    frame,
                    textvariable=self.type_var,
                    values=[row["name"] for row in self.types],
                    width=30,
                    state="readonly",
                )
                self.type_box.grid(row=row, column=1, sticky="ew", pady=4)
            else:
                ttk.Entry(frame, textvariable=variable, width=34).grid(row=row, column=1, sticky="ew", pady=4)

        actions = ttk.Frame(frame)
        actions.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Сохранить", command=self.save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Отмена", command=self.destroy).pack(side=tk.LEFT, padx=(8, 0))

    def load_material(self):
        material = self.database.fetch_material(self.material_id)
        if not material:
            messagebox.showerror("Ошибка", "Материал не найден")
            self.destroy()
            return

        type_index = next((i for i, item in enumerate(self.types) if item["id"] == material["type_id"]), 0)
        self.type_box.current(type_index)
        self.name_var.set(material["name"])
        self.price_var.set(f"{material['price']:.2f}")
        self.unit_var.set(material["unit"])
        self.pack_var.set(str(material["pack_quantity"]))
        self.stock_var.set(str(material["stock_quantity"]))
        self.min_var.set(str(material["min_quantity"]))

    def validate(self):
        errors = []
        if self.type_box.current() < 0:
            errors.append("Выберите тип материала")
        if not self.name_var.get().strip():
            errors.append("Введите наименование")
        if not self.unit_var.get().strip():
            errors.append("Введите единицу измерения")

        try:
            price = float(self.price_var.get())
            if price < 0:
                errors.append("Цена не может быть отрицательной")
        except ValueError:
            errors.append("Цена должна быть числом")

        for title, variable, minimum in [
            ("Количество в упаковке", self.pack_var, 1),
            ("Остаток", self.stock_var, 0),
            ("Минимальный остаток", self.min_var, 0),
        ]:
            try:
                value = int(variable.get())
                if value < minimum:
                    errors.append(f"{title}: значение должно быть не меньше {minimum}")
            except ValueError:
                errors.append(f"{title}: введите целое число")

        return errors

    def save(self):
        errors = self.validate()
        if errors:
            messagebox.showerror("Ошибка валидации", "\n".join(errors))
            return

        type_id = self.types[self.type_box.current()]["id"]
        values = (
            type_id,
            self.name_var.get().strip(),
            float(self.price_var.get()),
            self.unit_var.get().strip(),
            int(self.pack_var.get()),
            int(self.stock_var.get()),
            int(self.min_var.get()),
        )
        try:
            self.database.save_material(self.material_id, values)
        except sqlite3.Error as exc:
            messagebox.showerror("Ошибка БД", str(exc))
            return

        self.on_saved()
        self.destroy()


class MaterialApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.database = Database(DB_PATH)
        self.search_var = tk.StringVar()
        self.shortage_var = tk.BooleanVar(value=False)
        self.product_var = tk.StringVar()
        self.material_var = tk.StringVar()
        self.stock_var = tk.StringVar(value="10")
        self.param1_var = tk.StringVar(value="1")
        self.param2_var = tk.StringVar(value="1")
        self.products = []
        self.material_rows = []

        self.title("Вариант 5 - склад материалов")
        self.geometry("980x620")
        self.minsize(820, 480)

        self.build_ui()
        self.load_products()
        self.load_materials()

    def build_ui(self):
        toolbar = ttk.Frame(self, padding=(12, 12, 12, 6))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Поиск").pack(side=tk.LEFT)
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=28)
        search_entry.pack(side=tk.LEFT, padx=(6, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.load_materials())

        ttk.Checkbutton(
            toolbar,
            text="Только ниже минимума",
            variable=self.shortage_var,
            command=self.load_materials,
        ).pack(side=tk.LEFT)

        ttk.Button(toolbar, text="Обновить", command=self.load_materials).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(toolbar, text="Новый материал", command=self.open_create_form).pack(side=tk.RIGHT)

        columns = ("id", "type", "name", "price", "unit", "pack", "stock", "min", "required")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=13)
        headings = {
            "id": "№",
            "type": "Тип",
            "name": "Наименование",
            "price": "Цена",
            "unit": "Ед.",
            "pack": "Упак.",
            "stock": "Остаток",
            "min": "Минимум",
            "required": "Требуется",
        }
        widths = {
            "id": 55,
            "type": 145,
            "name": 230,
            "price": 95,
            "unit": 60,
            "pack": 70,
            "stock": 80,
            "min": 80,
            "required": 95,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            anchor = "e" if column in {"price", "pack", "stock", "min", "required"} else "w"
            if column == "id":
                anchor = "center"
            self.tree.column(column, width=widths[column], anchor=anchor)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.tree.tag_configure("shortage", background="#ffe7e7")
        self.tree.bind("<Double-1>", lambda _event: self.open_edit_form())

        actions = ttk.Frame(self, padding=(12, 0, 12, 8))
        actions.pack(fill=tk.X)
        ttk.Button(actions, text="Редактировать", command=self.open_edit_form).pack(side=tk.LEFT)
        ttk.Button(actions, text="Удалить", command=self.delete_selected).pack(side=tk.LEFT, padx=(8, 0))
        self.summary_label = ttk.Label(actions, text="")
        self.summary_label.pack(side=tk.RIGHT)

        calculator = ttk.LabelFrame(self, text="Расчет количества продукции", padding=12)
        calculator.pack(fill=tk.X, padx=12, pady=(0, 12))

        ttk.Label(calculator, text="Продукция").grid(row=0, column=0, sticky="w")
        self.product_box = ttk.Combobox(calculator, textvariable=self.product_var, state="readonly", width=26)
        self.product_box.grid(row=0, column=1, sticky="w", padx=(6, 14))

        ttk.Label(calculator, text="Материал").grid(row=0, column=2, sticky="w")
        self.material_box = ttk.Combobox(calculator, textvariable=self.material_var, state="readonly", width=28)
        self.material_box.grid(row=0, column=3, sticky="w", padx=(6, 14))

        ttk.Label(calculator, text="Остаток").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(calculator, textvariable=self.stock_var, width=10).grid(row=1, column=1, sticky="w", padx=(6, 14), pady=(8, 0))

        ttk.Label(calculator, text="Параметр 1").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(calculator, textvariable=self.param1_var, width=10).grid(row=1, column=3, sticky="w", padx=(6, 14), pady=(8, 0))

        ttk.Label(calculator, text="Параметр 2").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Entry(calculator, textvariable=self.param2_var, width=10).grid(row=1, column=5, sticky="w", padx=(6, 14), pady=(8, 0))

        ttk.Button(calculator, text="Рассчитать", command=self.calculate_product_count).grid(row=1, column=6, sticky="w", pady=(8, 0))
        self.result_label = ttk.Label(calculator, text="Результат: -")
        self.result_label.grid(row=1, column=7, sticky="w", padx=(14, 0), pady=(8, 0))

    def load_products(self):
        self.products = self.database.fetch_products()
        self.product_box["values"] = [row["name"] for row in self.products]
        if self.products:
            self.product_box.current(0)

    def load_materials(self):
        self.tree.delete(*self.tree.get_children())
        self.material_rows = self.database.fetch_materials(self.search_var.get(), self.shortage_var.get())
        self.material_box["values"] = [row["name"] for row in self.material_rows]
        if self.material_rows and self.material_box.current() < 0:
            self.material_box.current(0)

        stock_total = 0
        shortage_count = 0
        for row in self.material_rows:
            stock_total += row["stock_quantity"]
            tags = ()
            if row["stock_quantity"] < row["min_quantity"]:
                tags = ("shortage",)
                shortage_count += 1
            self.tree.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row["type_name"],
                    row["name"],
                    f"{row['price']:.2f}",
                    row["unit"],
                    row["pack_quantity"],
                    row["stock_quantity"],
                    row["min_quantity"],
                    row["required_total"],
                ),
                tags=tags,
            )
        self.summary_label.config(
            text=f"Материалов: {len(self.material_rows)} | Остаток: {stock_total} | Ниже минимума: {shortage_count}"
        )

    def selected_material_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Выбор материала", "Выберите материал в списке")
            return None
        return int(selected[0])

    def open_create_form(self):
        MaterialForm(self, self.database, self.load_materials)

    def open_edit_form(self):
        material_id = self.selected_material_id()
        if material_id is not None:
            MaterialForm(self, self.database, self.load_materials, material_id)

    def delete_selected(self):
        material_id = self.selected_material_id()
        if material_id is None:
            return
        if not messagebox.askyesno("Удаление", f"Удалить материал №{material_id}?"):
            return
        try:
            self.database.delete_material(material_id)
        except (sqlite3.Error, ValueError) as exc:
            messagebox.showerror("Ошибка удаления", str(exc))
            return
        self.load_materials()

    def calculate_product_count(self):
        product_index = self.product_box.current()
        material_index = self.material_box.current()
        if product_index < 0 or material_index < 0:
            messagebox.showerror("Ошибка", "Выберите продукцию и материал")
            return

        try:
            stock = int(self.stock_var.get())
            param1 = float(self.param1_var.get())
            param2 = float(self.param2_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Остаток должен быть целым числом, параметры - числами")
            return

        result = self.database.calculate_product_count(
            self.products[product_index]["id"],
            self.material_rows[material_index]["id"],
            stock,
            param1,
            param2,
        )
        if result == -1:
            self.result_label.config(text="Результат: некорректные данные")
        else:
            self.result_label.config(text=f"Результат: {result} шт.")


if __name__ == "__main__":
    app = MaterialApp()
    app.mainloop()
