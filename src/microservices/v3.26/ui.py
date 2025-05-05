from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import repositories
from database import APP_ASSETS_DIR, BASE_DIR, PRODUCT_IMAGES_DIR


WHITE = "#FFFFFF"
GOLD = "#DAA520"
ACCENT = "#B8860B"
DISCOUNT_BG = "#F4A460"
OUT_OF_STOCK_BG = "#BFEFFF"
FONT = ("Calibri", 12)
TITLE_FONT = ("Calibri", 18, "bold")
SMALL_FONT = ("Calibri", 10)


class StoreApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("СтройМатериалы - вход")
        self.geometry("1120x720")
        self.configure(bg=WHITE)
        self.current_user: dict[str, str] | None = None
        self.edit_window: ProductForm | None = None
        self.product_images: list[ImageTk.PhotoImage] = []

        icon_path = APP_ASSETS_DIR / "icon.png"
        if icon_path.exists():
            self.iconphoto(True, ImageTk.PhotoImage(Image.open(icon_path)))

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
        user = repositories.authenticate(login, password)
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

        content = tk.Frame(self, bg=WHITE)
        content.place(relx=0.5, rely=0.5, anchor="center")

        logo_path = APP_ASSETS_DIR / "icon.png"
        if logo_path.exists():
            image = Image.open(logo_path)
            image.thumbnail((160, 130), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(image)
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

            self.manufacturer_menu = ttk.Combobox(
                toolbar,
                textvariable=self.manufacturer_var,
                values=repositories.get_manufacturers(),
                state="readonly",
                width=24,
                font=FONT,
            )
            self.manufacturer_menu.pack(side="left", padx=6)

            ttk.Combobox(
                toolbar,
                textvariable=self.sort_var,
                values=list(repositories.SORT_FIELDS.keys()),
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

        products = repositories.get_products(
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

    def _product_row(self, product) -> tk.Frame:
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

    def _load_product_image(self, image_path: str | None) -> ImageTk.PhotoImage:
        path = BASE_DIR / image_path if image_path else APP_ASSETS_DIR / "picture.png"
        if not path.exists():
            path = APP_ASSETS_DIR / "picture.png"
        image = Image.open(path)
        image.thumbnail((120, 90), Image.LANCZOS)
        return ImageTk.PhotoImage(image)

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
        ok, message = repositories.delete_product(article)
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
        self.product = repositories.get_product(article) if article else None
        self.selected_image_path = self.product["image_path"] if self.product else None
        self.title("Добавление товара" if self.is_new else "Редактирование товара")
        self.geometry("620x650")
        self.configure(bg=WHITE)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.values: dict[str, tk.StringVar] = {
            "article": tk.StringVar(value=repositories.generate_article() if self.is_new else self.product["article"]),
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
        accent_button(form, "Выбрать изображение", self.choose_image).grid(row=4, column=0, sticky="ew", padx=(0, 18))

        self._entry(form, "Артикул", "article", 0, readonly=not self.is_new)
        self._entry(form, "Наименование", "name", 1)
        self._combo(form, "Категория", "category", repositories.get_lookup_values("categories"), 2)
        self._combo(form, "Производитель", "manufacturer", repositories.get_lookup_values("manufacturers"), 3)
        self._entry(form, "Поставщик", "supplier", 4)
        self._entry(form, "Цена", "price", 5)
        self._entry(form, "Единица измерения", "unit", 6)
        self._entry(form, "Количество", "stock_quantity", 7)
        self._entry(form, "Скидка", "discount", 8)

        tk.Label(form, text="Описание", bg=WHITE, font=FONT).grid(row=9, column=0, sticky="w", pady=6)
        self.description.grid(row=9, column=1, sticky="ew", pady=6)
        if self.product:
            self.description.insert("1.0", self.product["description"])

        buttons = tk.Frame(form, bg=WHITE)
        buttons.grid(row=10, column=0, columnspan=2, sticky="e", pady=18)
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
            title="Выберите изображение товара",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg"), ("Все файлы", "*.*")],
        )
        if path:
            self.selected_image_path = path
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        path = self._selected_image_absolute_path()
        image = Image.open(path)
        image.thumbnail((160, 120), Image.LANCZOS)
        self.preview_image = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_image)

    def _selected_image_absolute_path(self) -> Path:
        if self.selected_image_path:
            path = Path(self.selected_image_path)
            if not path.is_absolute():
                path = BASE_DIR / path
            if path.exists():
                return path
        return APP_ASSETS_DIR / "picture.png"

    def save(self) -> None:
        try:
            product = self._validated_product()
            product["image_path"] = self._save_image()
            repositories.save_product(product, self.is_new)
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
        if self.is_new and repositories.article_exists(article):
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
            "image_path": self.selected_image_path,
        }

    def _save_image(self) -> str | None:
        if not self.selected_image_path:
            return None

        selected_path = self._selected_image_absolute_path()
        if selected_path == APP_ASSETS_DIR / "picture.png":
            return None

        if str(self.selected_image_path).startswith("app_assets/product_images/"):
            return self.selected_image_path

        article = self.values["article"].get().strip()
        target = PRODUCT_IMAGES_DIR / f"{article}{selected_path.suffix.lower()}"
        image = Image.open(selected_path)
        image.thumbnail((300, 200), Image.LANCZOS)
        image.save(target)

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
        for order in repositories.get_orders():
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
