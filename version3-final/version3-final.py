#!/usr/bin/env python3
"""
LabEquipment Manager на Tkinter
Улучшенная версия с русскими статусами, управлением пользователями, 
оборудованием и гостевой доступом
"""
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, simpledialog
import sqlite3
from datetime import datetime

print("=== Запуск LabEquipment Manager ===")

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, db_name="lab_equipment.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.init_database()
        print("База данных инициализирована")
    
    def init_database(self):
        """Создание таблиц и тестовых данных"""
        # Таблица пользователей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                password TEXT NOT NULL
            )
        """)
        
        # Таблица оборудования
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                status TEXT DEFAULT 'available'
            )
        """)
        
        # Таблица заявок
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                equipment_id INTEGER NOT NULL,
                student_group TEXT NOT NULL,
                purpose TEXT NOT NULL,
                desired_date TEXT NOT NULL,
                desired_time_slot TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Проверяем наличие тестовых данных
        self.cursor.execute("SELECT COUNT(*) FROM users")
        if self.cursor.fetchone()[0] == 0:
            # Тестовые пользователи
            users = [
                ('admin', 'Администратор Системы', 'admin', 'admin123'),
                ('teacher1', 'Петров Иван Сергеевич', 'teacher', 'teacher1'),
                ('teacher2', 'Сидорова Мария Константиновна', 'teacher', 'teacher2')
            ]
            self.cursor.executemany(
                "INSERT INTO users (username, full_name, role, password) VALUES (?, ?, ?, ?)",
                users
            )
            
            # Тестовое оборудование
            equipment = [
                ('Микроскоп биологический', 'Увеличение 1000x, с иммерсионным маслом', 'available'),
                ('Осциллограф цифровой', '4 канала, 100 МГц, с памятью', 'available'),
                ('3D-принтер Creality', 'Область печати 220x220x250 мм', 'maintenance'),
                ('Спектрометр USB2000+', 'Диапазон 200-850 нм', 'available'),
                ('Центрифуга лабораторная', 'Макс. 10000 об/мин, 8 мест', 'in_use'),
                ('Термостат суховоздушный', 'Темп. диапазон +30..+300°C', 'available')
            ]
            self.cursor.executemany(
                "INSERT INTO equipment (name, description, status) VALUES (?, ?, ?)",
                equipment
            )
            
            # Тестовые заявки
            requests = [
                (2, 1, 'Био-21', 'Лабораторная работа по цитологии', '2024-12-15', '9:00-11:00', 'approved', 'Занятие подтверждено'),
                (2, 4, 'Физ-22', 'Исследование спектров поглощения', '2024-12-16', '13:00-15:00', 'pending', None),
                (3, 2, 'Радио-23', 'Изучение сигналов', '2024-12-17', '11:00-13:00', 'rejected', 'Оборудование на калибровке')
            ]
            self.cursor.executemany(
                """INSERT INTO requests 
                   (teacher_id, equipment_id, student_group, purpose, desired_date, 
                    desired_time_slot, status, admin_notes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                requests
            )
            
            self.connection.commit()
            print("Тестовые данные добавлены")
    
    def authenticate(self, username, password):
        """Аутентификация пользователя"""
        self.cursor.execute(
            "SELECT id, full_name, role FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        return self.cursor.fetchone()
    
    def get_available_equipment(self):
        """Получить доступное оборудование"""
        self.cursor.execute(
            "SELECT id, name, description FROM equipment WHERE status = 'available' ORDER BY name"
        )
        return self.cursor.fetchall()
    
    def get_all_equipment(self):
        """Получить всё оборудование"""
        self.cursor.execute(
            "SELECT id, name, description, status FROM equipment ORDER BY name"
        )
        return self.cursor.fetchall()
    
    def get_equipment_by_id(self, equipment_id):
        """Получить оборудование по ID"""
        self.cursor.execute(
            "SELECT id, name, description, status FROM equipment WHERE id = ?",
            (equipment_id,)
        )
        return self.cursor.fetchone()
    
    def add_equipment(self, name, description, status):
        """Добавить новое оборудование"""
        try:
            self.cursor.execute(
                "INSERT INTO equipment (name, description, status) VALUES (?, ?, ?)",
                (name, description, status)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_equipment(self, equipment_id, name, description, status):
        """Обновить данные оборудования"""
        try:
            self.cursor.execute(
                "UPDATE equipment SET name = ?, description = ?, status = ? WHERE id = ?",
                (name, description, status, equipment_id)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def delete_equipment(self, equipment_id):
        """Удалить оборудование"""
        # Сначала проверяем, есть ли заявки на это оборудование
        self.cursor.execute("SELECT COUNT(*) FROM requests WHERE equipment_id = ?", (equipment_id,))
        count = self.cursor.fetchone()[0]
        
        if count > 0:
            return False, f"На это оборудование есть {count} активных заявок. Сначала удалите их."
        
        try:
            self.cursor.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
            self.connection.commit()
            return True, "Оборудование успешно удалено"
        except:
            return False, "Не удалось удалить оборудование"
    
    def create_request(self, teacher_id, equipment_id, student_group, purpose, date, time_slot):
        """Создать новую заявку"""
        self.cursor.execute(
            """INSERT INTO requests 
               (teacher_id, equipment_id, student_group, purpose, desired_date, desired_time_slot) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (teacher_id, equipment_id, student_group, purpose, date, time_slot)
        )
        self.connection.commit()
        return self.cursor.lastrowid
    
    def get_teacher_requests(self, teacher_id):
        """Получить заявки преподавателя"""
        self.cursor.execute("""
            SELECT r.id, e.name, r.student_group, r.purpose, r.desired_date,
                   r.desired_time_slot, r.status, r.admin_notes
            FROM requests r
            JOIN equipment e ON r.equipment_id = e.id
            WHERE r.teacher_id = ?
            ORDER BY r.desired_date DESC
        """, (teacher_id,))
        return self.cursor.fetchall()
    
    def get_all_requests(self):
        """Получить все заявки (для администратора)"""
        self.cursor.execute("""
            SELECT r.id, u.full_name, e.name, r.student_group, r.purpose,
                   r.desired_date, r.desired_time_slot, r.status, r.admin_notes
            FROM requests r
            JOIN users u ON r.teacher_id = u.id
            JOIN equipment e ON r.equipment_id = e.id
            ORDER BY CASE r.status 
                WHEN 'pending' THEN 1
                WHEN 'approved' THEN 2
                WHEN 'rejected' THEN 3
                WHEN 'completed' THEN 4
                ELSE 5 END, r.desired_date
        """)
        return self.cursor.fetchall()
    
    def update_request_status(self, request_id, status, notes=None):
        """Обновить статус заявки"""
        if notes:
            self.cursor.execute(
                "UPDATE requests SET status = ?, admin_notes = ? WHERE id = ?",
                (status, notes, request_id)
            )
        else:
            self.cursor.execute(
                "UPDATE requests SET status = ? WHERE id = ?",
                (status, request_id)
            )
        self.connection.commit()
    
    def get_all_users(self, exclude_admin=True):
        """Получить всех пользователей"""
        if exclude_admin:
            self.cursor.execute(
                "SELECT id, username, full_name, role FROM users WHERE role != 'admin' ORDER BY full_name"
            )
        else:
            self.cursor.execute(
                "SELECT id, username, full_name, role FROM users ORDER BY full_name"
            )
        return self.cursor.fetchall()
    
    def add_user(self, username, full_name, role, password):
        """Добавить нового пользователя"""
        try:
            self.cursor.execute(
                "INSERT INTO users (username, full_name, role, password) VALUES (?, ?, ?, ?)",
                (username, full_name, role, password)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_user(self, user_id, username, full_name, role, password=None):
        """Обновить данные пользователя"""
        if password:
            self.cursor.execute(
                "UPDATE users SET username = ?, full_name = ?, role = ?, password = ? WHERE id = ?",
                (username, full_name, role, password, user_id)
            )
        else:
            self.cursor.execute(
                "UPDATE users SET username = ?, full_name = ?, role = ? WHERE id = ?",
                (username, full_name, role, user_id)
            )
        self.connection.commit()
    
    def delete_user(self, user_id):
        """Удалить пользователя"""
        # Сначала проверяем, есть ли заявки у пользователя
        self.cursor.execute("SELECT COUNT(*) FROM requests WHERE teacher_id = ?", (user_id,))
        count = self.cursor.fetchone()[0]
        
        if count > 0:
            return False, f"У пользователя есть {count} активных заявок. Сначала удалите их."
        
        try:
            self.cursor.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,))
            self.connection.commit()
            return True, "Пользователь успешно удален"
        except:
            return False, "Не удалось удалить пользователя"
    
    def get_user_by_id(self, user_id):
        """Получить пользователя по ID"""
        self.cursor.execute(
            "SELECT id, username, full_name, role FROM users WHERE id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()
    
    def get_equipment_status_stats(self):
        """Получить статистику по статусам оборудования"""
        self.cursor.execute("""
            SELECT status, COUNT(*) as count FROM equipment GROUP BY status
        """)
        return self.cursor.fetchall()
    
    def get_request_status_stats(self):
        """Получить статистику по статусам заявок"""
        self.cursor.execute("""
            SELECT status, COUNT(*) as count FROM requests GROUP BY status
        """)
        return self.cursor.fetchall()
    
    def close(self):
        """Закрыть соединение с БД"""
        self.connection.close()

class LoginWindow:
    """Окно входа"""
    
    def __init__(self, root, db_manager):
        self.root = root
        self.db = db_manager
        self.root.title("LabEquipment Manager - Вход")
        self.root.geometry("450x350")
        self.root.resizable(True, True)  # Разрешаем изменение размера
        
        # Центрирование окна
        self.center_window(450, 350)
        
        self.create_widgets()
    
    def center_window(self, width, height):
        """Центрировать окно на экране"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Создание виджетов окна входа"""
        # Главный фрейм с отступами
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Заголовок
        title_label = tk.Label(
            main_frame, 
            text="LabEquipment Manager",
            font=("Arial", 18, "bold"),
            fg="#2196F3"
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(
            main_frame,
            text="Система учета лабораторного оборудования",
            font=("Arial", 10),
            fg="gray"
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Фрейм для полей ввода
        input_frame = tk.Frame(main_frame)
        input_frame.pack(pady=10)
        
        # Логин
        tk.Label(input_frame, text="Логин:", font=("Arial", 11)).grid(
            row=0, column=0, padx=10, pady=10, sticky="e"
        )
        self.username_entry = tk.Entry(input_frame, font=("Arial", 11), width=20)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        self.username_entry.focus()
        
        # Пароль
        tk.Label(input_frame, text="Пароль:", font=("Arial", 11)).grid(
            row=1, column=0, padx=10, pady=10, sticky="e"
        )
        self.password_entry = tk.Entry(
            input_frame, font=("Arial", 11), width=20, show="*"
        )
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)
        
        # Фрейм для кнопок
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        # Кнопка входа
        login_button = tk.Button(
            button_frame, 
            text="Войти", 
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=25,
            pady=5,
            command=self.login
        )
        login_button.pack(side="left", padx=5)
        
        # Кнопка гостевого входа
        guest_button = tk.Button(
            button_frame,
            text="Гостевой доступ",
            font=("Arial", 11),
            bg="#FF9800",
            fg="white",
            padx=15,
            pady=5,
            command=self.guest_login
        )
        guest_button.pack(side="left", padx=5)
        
        # Связываем Enter с кнопкой входа
        self.root.bind('<Return>', lambda event: self.login())
    
    def login(self):
        """Обработка входа"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Ошибка", "Заполните все поля")
            return
        
        user = self.db.authenticate(username, password)
        if user:
            user_id, full_name, role = user
            messagebox.showinfo("Успех", f"Добро пожаловать, {full_name}!")
            self.root.destroy()  # Закрыть окно входа
            
            # Открыть главное окно
            if role == 'teacher':
                app = TeacherApp(user_id, full_name, self.db)
            else:
                app = AdminApp(user_id, full_name, self.db)
            app.run()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
    
    def guest_login(self):
        """Гостевой доступ"""
        self.root.destroy()
        app = GuestApp(self.db)
        app.run()

class TeacherApp:
    """Приложение для преподавателя"""
    
    def __init__(self, user_id, full_name, db_manager):
        self.user_id = user_id
        self.full_name = full_name
        self.db = db_manager
        self.root = tk.Tk()
        self.root.title(f"LabEquipment Manager - Преподаватель ({full_name})")
        self.root.geometry("1100x750")
        self.root.resizable(True, True)  # Разрешаем изменение размера
        self.center_window(1100, 750)
        
        # Словарь для перевода статусов
        self.status_translation = {
            'pending': 'На рассмотрении',
            'approved': 'Одобрено',
            'rejected': 'Отклонено',
            'completed': 'Завершено'
        }
        
        self.create_widgets()
        self.load_requests()
    
    def center_window(self, width, height):
        """Центрировать окно"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Создание интерфейса преподавателя"""
        # Заголовок
        header_frame = tk.Frame(self.root, bg="#2196F3")
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = tk.Label(
            header_frame,
            text=f"Добро пожаловать, {self.full_name}!",
            font=("Arial", 14, "bold"),
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=10
        )
        title_label.pack(side="left")
        
        # Панель вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Вкладка 1: Новая заявка
        self.create_new_request_tab()
        
        # Вкладка 2: Мои заявки
        self.create_my_requests_tab()
        
        # Кнопка выхода
        exit_button = tk.Button(
            self.root,
            text="Выход",
            font=("Arial", 10),
            command=self.root.destroy,
            padx=15,
            pady=5
        )
        exit_button.pack(pady=10)
    
    def create_new_request_tab(self):
        """Создать вкладку для новой заявки"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Новая заявка")
        
        # Контейнер с прокруткой
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Поля формы
        fields_frame = tk.Frame(scrollable_frame)
        fields_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Оборудование
        tk.Label(fields_frame, text="Оборудование:", font=("Arial", 11)).grid(
            row=0, column=0, sticky="w", pady=10
        )
        self.equipment_combo = ttk.Combobox(fields_frame, font=("Arial", 11), width=40)
        self.equipment_combo.grid(row=0, column=1, pady=10, padx=(10, 0))
        self.load_equipment_list()
        
        # Учебная группа
        tk.Label(fields_frame, text="Учебная группа:", font=("Arial", 11)).grid(
            row=1, column=0, sticky="w", pady=10
        )
        self.group_entry = tk.Entry(fields_frame, font=("Arial", 11), width=30)
        self.group_entry.grid(row=1, column=1, pady=10, padx=(10, 0))
        
        # Цель использования
        tk.Label(fields_frame, text="Цель использования:", font=("Arial", 11)).grid(
            row=2, column=0, sticky="nw", pady=10
        )
        self.purpose_text = tk.Text(fields_frame, font=("Arial", 11), width=40, height=5)
        self.purpose_text.grid(row=2, column=1, pady=10, padx=(10, 0))
        
        # Желаемая дата
        tk.Label(fields_frame, text="Желаемая дата:", font=("Arial", 11)).grid(
            row=3, column=0, sticky="w", pady=10
        )
        self.date_entry = tk.Entry(fields_frame, font=("Arial", 11), width=20)
        self.date_entry.grid(row=3, column=1, sticky="w", pady=10, padx=(10, 0))
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Временной слот
        tk.Label(fields_frame, text="Временной слот:", font=("Arial", 11)).grid(
            row=4, column=0, sticky="w", pady=10
        )
        self.time_combo = ttk.Combobox(fields_frame, font=("Arial", 11), width=20)
        self.time_combo['values'] = ('9:00-11:00', '11:00-13:00', '13:00-15:00', '15:00-17:00')
        self.time_combo.current(0)
        self.time_combo.grid(row=4, column=1, sticky="w", pady=10, padx=(10, 0))
        
        # Кнопка подачи заявки
        submit_button = tk.Button(
            fields_frame,
            text="Подать заявку",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=5,
            command=self.submit_request
        )
        submit_button.grid(row=5, column=1, sticky="w", pady=20, padx=(10, 0))
        
        # Упаковка канваса и скроллбара
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_my_requests_tab(self):
        """Создать вкладку с заявками преподавателя"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Мои заявки")
        
        # Контейнер для таблицы
        table_container = tk.Frame(tab)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Таблица заявок
        columns = ("ID", "Оборудование", "Группа", "Цель", "Дата", "Время", "Статус", "Комментарий")
        self.requests_tree = ttk.Treeview(table_container, columns=columns, show="headings")
        
        # Настройка колонок
        col_widths = [50, 150, 80, 200, 100, 100, 100, 150]
        for col, width in zip(columns, col_widths):
            self.requests_tree.heading(col, text=col)
            self.requests_tree.column(col, width=width, minwidth=50)
        
        # Полосы прокрутки
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.requests_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.requests_tree.xview)
        self.requests_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещение с помощью grid
        self.requests_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Настройка весов для расширения
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Кнопка обновления
        refresh_button = tk.Button(
            tab,
            text="Обновить список",
            font=("Arial", 10),
            command=self.load_requests,
            padx=15,
            pady=5
        )
        refresh_button.pack(pady=10)
    
    def load_equipment_list(self):
        """Загрузить список доступного оборудования"""
        equipment = self.db.get_available_equipment()
        equipment_list = []
        self.equipment_map = {}
        
        for eq_id, name, desc in equipment:
            display_text = f"{name} ({desc})"
            equipment_list.append(display_text)
            self.equipment_map[display_text] = eq_id
        
        self.equipment_combo['values'] = equipment_list
        if equipment_list:
            self.equipment_combo.current(0)
    
    def load_requests(self):
        """Загрузить заявки преподавателя"""
        # Очистить таблицу
        for item in self.requests_tree.get_children():
            self.requests_tree.delete(item)
        
        # Загрузить данные
        requests = self.db.get_teacher_requests(self.user_id)
        for req in requests:
            # Преобразование статуса
            original_status = req[6]
            translated_status = self.status_translation.get(original_status, original_status)
            
            # Создание новой строки с переведенным статусом
            translated_req = list(req)
            translated_req[6] = translated_status
            
            # Подсветка статуса
            tags = ()
            if original_status == 'approved':
                tags = ('approved',)
            elif original_status == 'rejected':
                tags = ('rejected',)
            elif original_status == 'pending':
                tags = ('pending',)
            
            self.requests_tree.insert("", "end", values=translated_req, tags=tags)
        
        # Настройка цветов
        self.requests_tree.tag_configure('approved', background='#d4edda')
        self.requests_tree.tag_configure('rejected', background='#f8d7da')
        self.requests_tree.tag_configure('pending', background='#fff3cd')
    
    def submit_request(self):
        """Подать новую заявку"""
        # Получение данных из формы
        equipment_text = self.equipment_combo.get()
        if not equipment_text or equipment_text not in self.equipment_map:
            messagebox.showerror("Ошибка", "Выберите оборудование из списка")
            return
        
        equipment_id = self.equipment_map[equipment_text]
        group = self.group_entry.get().strip()
        purpose = self.purpose_text.get("1.0", "end").strip()
        date = self.date_entry.get().strip()
        time_slot = self.time_combo.get()
        
        if not all([group, purpose, date]):
            messagebox.showerror("Ошибка", "Заполните все обязательные поля")
            return
        
        # Создание заявки
        try:
            request_id = self.db.create_request(
                self.user_id, equipment_id, group, purpose, date, time_slot
            )
            messagebox.showinfo("Успех", f"Заявка #{request_id} успешно создана!")
            
            # Очистка формы
            self.group_entry.delete(0, tk.END)
            self.purpose_text.delete("1.0", tk.END)
            self.load_equipment_list()
            self.load_requests()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать заявку: {str(e)}")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

class AdminApp:
    """Приложение для администратора"""
    
    def __init__(self, user_id, full_name, db_manager):
        self.user_id = user_id
        self.full_name = full_name
        self.db = db_manager
        self.root = tk.Tk()
        self.root.title(f"LabEquipment Manager - Администратор ({full_name})")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)  # Разрешаем изменение размера
        self.center_window(1400, 900)
        
        # Словарь для перевода статусов
        self.status_translation = {
            'pending': 'На рассмотрении',
            'approved': 'Одобрено',
            'rejected': 'Отклонено',
            'completed': 'Завершено'
        }
        
        # Словарь для статусов оборудования
        self.equip_status_translation = {
            'available': 'Доступно',
            'in_use': 'В использовании',
            'maintenance': 'На обслуживании'
        }
        
        # Обратные словари
        self.reverse_status_translation = {v: k for k, v in self.status_translation.items()}
        self.reverse_equip_status_translation = {v: k for k, v in self.equip_status_translation.items()}
        
        self.create_widgets()
        self.load_all_requests()
    
    def center_window(self, width, height):
        """Центрировать окно"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Создание интерфейса администратора"""
        # Заголовок
        header_frame = tk.Frame(self.root, bg="#9C27B0")
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = tk.Label(
            header_frame,
            text=f"Панель администратора | Пользователь: {self.full_name}",
            font=("Arial", 14, "bold"),
            bg="#9C27B0",
            fg="white",
            padx=20,
            pady=10
        )
        title_label.pack(side="left")
        
        # Панель вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Вкладка 1: Управление заявками
        self.create_requests_tab()
        
        # Вкладка 2: Управление пользователями
        self.create_users_tab()
        
        # Вкладка 3: Управление оборудованием
        self.create_equipment_tab()
        
        # Вкладка 4: Статистика
        self.create_stats_tab()
    
    def create_requests_tab(self):
        """Создать вкладку управления заявками"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Управление заявками")
        
        # Контейнер для таблицы
        table_container = tk.Frame(tab)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Таблица всех заявок
        columns = ("ID", "Преподаватель", "Оборудование", "Группа", "Цель", "Дата", "Время", "Статус", "Комментарий")
        self.requests_tree = ttk.Treeview(table_container, columns=columns, show="headings")
        
        # Настройка колонок
        col_widths = [50, 150, 150, 80, 200, 100, 100, 100, 200]
        for col, width in zip(columns, col_widths):
            self.requests_tree.heading(col, text=col)
            self.requests_tree.column(col, width=width, minwidth=50)
        
        # Полосы прокрутки
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.requests_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.requests_tree.xview)
        self.requests_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещение с помощью grid
        self.requests_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Настройка весов для расширения
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Панель управления
        control_frame = tk.Frame(tab)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Выбор статуса
        tk.Label(control_frame, text="Новый статус:", font=("Arial", 11)).pack(side="left", padx=5)
        self.status_combo = ttk.Combobox(
            control_frame, 
            values=list(self.status_translation.values()), 
            width=15
        )
        self.status_combo.current(0)
        self.status_combo.pack(side="left", padx=5)
        
        # Комментарий
        tk.Label(control_frame, text="Комментарий:", font=("Arial", 11)).pack(side="left", padx=(20, 5))
        self.notes_entry = tk.Entry(control_frame, width=40, font=("Arial", 11))
        self.notes_entry.pack(side="left", padx=5)
        
        # Кнопки
        update_button = tk.Button(
            control_frame,
            text="Обновить статус",
            font=("Arial", 11, "bold"),
            bg="#2196F3",
            fg="white",
            command=self.update_status,
            padx=15,
            pady=5
        )
        update_button.pack(side="left", padx=10)
        
        refresh_button = tk.Button(
            control_frame,
            text="Обновить все",
            font=("Arial", 11),
            command=self.load_all_requests,
            padx=15,
            pady=5
        )
        refresh_button.pack(side="left", padx=5)
    
    def create_users_tab(self):
        """Создать вкладку управления пользователями"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Управление пользователями")
        
        # Контейнер для таблицы
        table_container = tk.Frame(tab)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Таблица пользователей
        columns = ("ID", "Логин", "ФИО", "Роль")
        self.users_tree = ttk.Treeview(table_container, columns=columns, show="headings")
        
        # Настройка колонок
        col_widths = [50, 150, 250, 100]
        for col, width in zip(columns, col_widths):
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=width, minwidth=50)
        
        # Полосы прокрутки
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.users_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.users_tree.xview)
        self.users_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещение с помощью grid
        self.users_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Настройка весов для расширения
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Панель управления пользователями
        user_control_frame = tk.Frame(tab)
        user_control_frame.pack(fill="x", padx=10, pady=10)
        
        # Кнопки управления пользователями
        add_user_button = tk.Button(
            user_control_frame,
            text="Добавить пользователя",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            command=self.add_user,
            padx=15,
            pady=5
        )
        add_user_button.pack(side="left", padx=5)
        
        edit_user_button = tk.Button(
            user_control_frame,
            text="Редактировать",
            font=("Arial", 11),
            bg="#FF9800",
            fg="white",
            command=self.edit_user,
            padx=15,
            pady=5
        )
        edit_user_button.pack(side="left", padx=5)
        
        delete_user_button = tk.Button(
            user_control_frame,
            text="Удалить",
            font=("Arial", 11),
            bg="#F44336",
            fg="white",
            command=self.delete_user,
            padx=15,
            pady=5
        )
        delete_user_button.pack(side="left", padx=5)
        
        refresh_users_button = tk.Button(
            user_control_frame,
            text="Обновить список",
            font=("Arial", 11),
            command=self.load_users,
            padx=15,
            pady=5
        )
        refresh_users_button.pack(side="left", padx=5)
        
        # Загрузка пользователей
        self.load_users()
    
    def create_equipment_tab(self):
        """Создать вкладку управления оборудованием"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Управление оборудованием")
        
        # Контейнер для таблицы
        table_container = tk.Frame(tab)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Таблица оборудования
        columns = ("ID", "Название", "Описание", "Статус")
        self.equipment_tree = ttk.Treeview(table_container, columns=columns, show="headings")
        
        # Настройка колонок
        col_widths = [50, 200, 300, 120]
        for col, width in zip(columns, col_widths):
            self.equipment_tree.heading(col, text=col)
            self.equipment_tree.column(col, width=width, minwidth=50)
        
        # Полосы прокрутки
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.equipment_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.equipment_tree.xview)
        self.equipment_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещение с помощью grid
        self.equipment_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Настройка весов для расширения
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Панель управления оборудованием
        equip_control_frame = tk.Frame(tab)
        equip_control_frame.pack(fill="x", padx=10, pady=10)
        
        # Кнопки управления оборудованием
        add_equip_button = tk.Button(
            equip_control_frame,
            text="Добавить оборудование",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            command=self.add_equipment,
            padx=15,
            pady=5
        )
        add_equip_button.pack(side="left", padx=5)
        
        edit_equip_button = tk.Button(
            equip_control_frame,
            text="Редактировать",
            font=("Arial", 11),
            bg="#FF9800",
            fg="white",
            command=self.edit_equipment,
            padx=15,
            pady=5
        )
        edit_equip_button.pack(side="left", padx=5)
        
        delete_equip_button = tk.Button(
            equip_control_frame,
            text="Удалить",
            font=("Arial", 11),
            bg="#F44336",
            fg="white",
            command=self.delete_equipment,
            padx=15,
            pady=5
        )
        delete_equip_button.pack(side="left", padx=5)
        
        refresh_equip_button = tk.Button(
            equip_control_frame,
            text="Обновить список",
            font=("Arial", 11),
            command=self.load_equipment,
            padx=15,
            pady=5
        )
        refresh_equip_button.pack(side="left", padx=5)
        
        # Загрузка оборудования
        self.load_equipment()
    
    def create_stats_tab(self):
        """Создать вкладку со статистикой"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Статистика")
        
        # Фрейм для статистики с прокруткой
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Статистика оборудования
        equip_stats_label = tk.Label(
            scrollable_frame,
            text="Статистика оборудования:",
            font=("Arial", 12, "bold")
        )
        equip_stats_label.grid(row=0, column=0, sticky="w", pady=(20, 10), padx=20)
        
        self.equip_stats_text = tk.Text(scrollable_frame, width=50, height=10, font=("Arial", 10))
        self.equip_stats_text.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        
        # Статистика заявок
        request_stats_label = tk.Label(
            scrollable_frame,
            text="Статистика заявок:",
            font=("Arial", 12, "bold")
        )
        request_stats_label.grid(row=0, column=1, sticky="w", pady=(20, 10), padx=20)
        
        self.request_stats_text = tk.Text(scrollable_frame, width=50, height=10, font=("Arial", 10))
        self.request_stats_text.grid(row=1, column=1, sticky="w", padx=20, pady=(0, 20))
        
        # Кнопка обновления статистики
        refresh_stats_button = tk.Button(
            scrollable_frame,
            text="Обновить статистику",
            font=("Arial", 11),
            command=self.load_stats,
            padx=15,
            pady=5
        )
        refresh_stats_button.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Кнопка выхода
        exit_button = tk.Button(
            scrollable_frame,
            text="Выход",
            font=("Arial", 11),
            command=self.root.destroy,
            padx=15,
            pady=5
        )
        exit_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Упаковка канваса и скроллбара
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Загрузка статистики
        self.load_stats()
    
    def load_all_requests(self):
        """Загрузить все заявки"""
        # Очистить таблицу
        for item in self.requests_tree.get_children():
            self.requests_tree.delete(item)
        
        # Загрузить данные
        requests = self.db.get_all_requests()
        for req in requests:
            # Преобразование статуса
            original_status = req[7]
            translated_status = self.status_translation.get(original_status, original_status)
            
            # Создание новой строки с переведенным статусом
            translated_req = list(req)
            translated_req[7] = translated_status
            
            # Подсветка статуса
            tags = ()
            if original_status == 'approved':
                tags = ('approved',)
            elif original_status == 'rejected':
                tags = ('rejected',)
            elif original_status == 'pending':
                tags = ('pending',)
            elif original_status == 'completed':
                tags = ('completed',)
            
            self.requests_tree.insert("", "end", values=translated_req, tags=tags)
        
        # Настройка цветов
        self.requests_tree.tag_configure('approved', background='#d4edda')
        self.requests_tree.tag_configure('rejected', background='#f8d7da')
        self.requests_tree.tag_configure('pending', background='#fff3cd')
        self.requests_tree.tag_configure('completed', background='#e2e3e5')
    
    def update_status(self):
        """Обновить статус выбранной заявки"""
        selection = self.requests_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заявку из таблицы")
            return
        
        item = selection[0]
        request_id = self.requests_tree.item(item)['values'][0]
        translated_status = self.status_combo.get()
        
        # Преобразование статуса обратно в английский
        original_status = self.reverse_status_translation.get(translated_status, translated_status)
        
        notes = self.notes_entry.get().strip() or None
        
        try:
            self.db.update_request_status(request_id, original_status, notes)
            messagebox.showinfo("Успех", f"Статус заявки #{request_id} обновлен")
            self.notes_entry.delete(0, tk.END)
            self.load_all_requests()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить статус: {str(e)}")
    
    def load_users(self):
        """Загрузить список пользователей"""
        # Очистить таблицу
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        # Загрузить данные
        users = self.db.get_all_users()
        for user in users:
            self.users_tree.insert("", "end", values=user)
    
    def load_equipment(self):
        """Загрузить оборудование"""
        # Очистить таблицу
        for item in self.equipment_tree.get_children():
            self.equipment_tree.delete(item)
        
        # Загрузить данные
        equipment = self.db.get_all_equipment()
        
        for eq in equipment:
            eq_id, name, desc, status = eq
            translated_status = self.equip_status_translation.get(status, status)
            
            # Подсветка статуса
            tags = ()
            if status == 'available':
                tags = ('available',)
            elif status == 'in_use':
                tags = ('in_use',)
            elif status == 'maintenance':
                tags = ('maintenance',)
            
            self.equipment_tree.insert("", "end", 
                                     values=(eq_id, name, desc, translated_status), 
                                     tags=tags)
        
        # Настройка цветов
        self.equipment_tree.tag_configure('available', background='#d4edda')
        self.equipment_tree.tag_configure('in_use', background='#fff3cd')
        self.equipment_tree.tag_configure('maintenance', background='#f8d7da')
    
    def add_user(self):
        """Добавить нового пользователя"""
        dialog = Toplevel(self.root)
        dialog.title("Добавить пользователя")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрирование диалога
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Поля формы
        tk.Label(dialog, text="Логин:", font=("Arial", 11)).pack(pady=(20, 5))
        username_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        username_entry.pack()
        
        tk.Label(dialog, text="ФИО:", font=("Arial", 11)).pack(pady=(10, 5))
        fullname_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        fullname_entry.pack()
        
        tk.Label(dialog, text="Пароль:", font=("Arial", 11)).pack(pady=(10, 5))
        password_entry = tk.Entry(dialog, font=("Arial", 11), width=30, show="*")
        password_entry.pack()
        
        tk.Label(dialog, text="Роль:", font=("Arial", 11)).pack(pady=(10, 5))
        role_combo = ttk.Combobox(dialog, values=['teacher', 'admin'], width=28)
        role_combo.current(0)
        role_combo.pack()
        
        def save_user():
            username = username_entry.get().strip()
            full_name = fullname_entry.get().strip()
            password = password_entry.get().strip()
            role = role_combo.get()
            
            if not all([username, full_name, password]):
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            
            if self.db.add_user(username, full_name, role, password):
                messagebox.showinfo("Успех", "Пользователь успешно добавлен")
                self.load_users()
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует")
        
        # Кнопки
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Сохранить",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=15,
            pady=5,
            command=save_user
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Отмена",
            font=("Arial", 11),
            padx=15,
            pady=5,
            command=dialog.destroy
        ).pack(side="left", padx=5)
    
    def edit_user(self):
        """Редактировать пользователя"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя из таблицы")
            return
        
        item = selection[0]
        user_id = self.users_tree.item(item)['values'][0]
        
        # Получить данные пользователя
        user = self.db.get_user_by_id(user_id)
        if not user:
            messagebox.showerror("Ошибка", "Пользователь не найден")
            return
        
        dialog = Toplevel(self.root)
        dialog.title("Редактировать пользователя")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрирование диалога
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Поля формы
        tk.Label(dialog, text="Логин:", font=("Arial", 11)).pack(pady=(20, 5))
        username_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        username_entry.insert(0, user[1])
        username_entry.pack()
        
        tk.Label(dialog, text="ФИО:", font=("Arial", 11)).pack(pady=(10, 5))
        fullname_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        fullname_entry.insert(0, user[2])
        fullname_entry.pack()
        
        tk.Label(dialog, text="Новый пароль (оставьте пустым, чтобы не менять):", 
                font=("Arial", 10)).pack(pady=(10, 5))
        password_entry = tk.Entry(dialog, font=("Arial", 11), width=30, show="*")
        password_entry.pack()
        
        tk.Label(dialog, text="Роль:", font=("Arial", 11)).pack(pady=(10, 5))
        role_combo = ttk.Combobox(dialog, values=['teacher', 'admin'], width=28)
        role_combo.set(user[3])
        role_combo.pack()
        
        def save_changes():
            username = username_entry.get().strip()
            full_name = fullname_entry.get().strip()
            password = password_entry.get().strip()
            role = role_combo.get()
            
            if not all([username, full_name]):
                messagebox.showerror("Ошибка", "Заполните обязательные поля")
                return
            
            self.db.update_user(user_id, username, full_name, role, password if password else None)
            messagebox.showinfo("Успех", "Данные пользователя обновлены")
            self.load_users()
            dialog.destroy()
        
        # Кнопки
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Сохранить",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=15,
            pady=5,
            command=save_changes
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Отмена",
            font=("Arial", 11),
            padx=15,
            pady=5,
            command=dialog.destroy
        ).pack(side="left", padx=5)
    
    def delete_user(self):
        """Удалить пользователя"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя из таблицы")
            return
        
        item = selection[0]
        user_id = self.users_tree.item(item)['values'][0]
        username = self.users_tree.item(item)['values'][1]
        
        # Подтверждение удаления
        if not messagebox.askyesno("Подтверждение", 
                                  f"Вы действительно хотите удалить пользователя {username}?"):
            return
        
        # Удаление пользователя
        success, message = self.db.delete_user(user_id)
        if success:
            messagebox.showinfo("Успех", message)
            self.load_users()
        else:
            messagebox.showerror("Ошибка", message)
    
    def add_equipment(self):
        """Добавить новое оборудование"""
        dialog = Toplevel(self.root)
        dialog.title("Добавить оборудование")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрирование диалога
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Поля формы
        tk.Label(dialog, text="Название оборудования:", font=("Arial", 11)).pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        name_entry.pack()
        
        tk.Label(dialog, text="Описание:", font=("Arial", 11)).pack(pady=(10, 5))
        desc_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        desc_entry.pack()
        
        tk.Label(dialog, text="Статус:", font=("Arial", 11)).pack(pady=(10, 5))
        status_combo = ttk.Combobox(dialog, 
                                   values=list(self.equip_status_translation.values()), 
                                   width=28)
        status_combo.current(0)
        status_combo.pack()
        
        def save_equipment():
            name = name_entry.get().strip()
            description = desc_entry.get().strip()
            translated_status = status_combo.get()
            
            # Преобразование статуса обратно в английский
            original_status = self.reverse_equip_status_translation.get(translated_status, translated_status)
            
            if not name:
                messagebox.showerror("Ошибка", "Введите название оборудования")
                return
            
            if self.db.add_equipment(name, description, original_status):
                messagebox.showinfo("Успех", "Оборудование успешно добавлено")
                self.load_equipment()
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Оборудование с таким названием уже существует")
        
        # Кнопки
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Сохранить",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=15,
            pady=5,
            command=save_equipment
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Отмена",
            font=("Arial", 11),
            padx=15,
            pady=5,
            command=dialog.destroy
        ).pack(side="left", padx=5)
    
    def edit_equipment(self):
        """Редактировать оборудование"""
        selection = self.equipment_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите оборудование из таблицы")
            return
        
        item = selection[0]
        equip_id = self.equipment_tree.item(item)['values'][0]
        
        # Получить данные оборудования
        equipment = self.db.get_equipment_by_id(equip_id)
        if not equipment:
            messagebox.showerror("Ошибка", "Оборудование не найдено")
            return
        
        dialog = Toplevel(self.root)
        dialog.title("Редактировать оборудование")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрирование диалога
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Поля формы
        tk.Label(dialog, text="Название оборудования:", font=("Arial", 11)).pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        name_entry.insert(0, equipment[1])
        name_entry.pack()
        
        tk.Label(dialog, text="Описание:", font=("Arial", 11)).pack(pady=(10, 5))
        desc_entry = tk.Entry(dialog, font=("Arial", 11), width=30)
        desc_entry.insert(0, equipment[2])
        desc_entry.pack()
        
        tk.Label(dialog, text="Статус:", font=("Arial", 11)).pack(pady=(10, 5))
        status_combo = ttk.Combobox(dialog, 
                                   values=list(self.equip_status_translation.values()), 
                                   width=28)
        
        # Установка текущего статуса
        current_status = self.equip_status_translation.get(equipment[3], equipment[3])
        status_combo.set(current_status)
        status_combo.pack()
        
        def save_changes():
            name = name_entry.get().strip()
            description = desc_entry.get().strip()
            translated_status = status_combo.get()
            
            # Преобразование статуса обратно в английский
            original_status = self.reverse_equip_status_translation.get(translated_status, translated_status)
            
            if not name:
                messagebox.showerror("Ошибка", "Введите название оборудования")
                return
            
            if self.db.update_equipment(equip_id, name, description, original_status):
                messagebox.showinfo("Успех", "Данные оборудования обновлены")
                self.load_equipment()
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Оборудование с таким названием уже существует")
        
        # Кнопки
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Сохранить",
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=15,
            pady=5,
            command=save_changes
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="Отмена",
            font=("Arial", 11),
            padx=15,
            pady=5,
            command=dialog.destroy
        ).pack(side="left", padx=5)
    
    def delete_equipment(self):
        """Удалить оборудование"""
        selection = self.equipment_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите оборудование из таблицы")
            return
        
        item = selection[0]
        equip_id = self.equipment_tree.item(item)['values'][0]
        equip_name = self.equipment_tree.item(item)['values'][1]
        
        # Подтверждение удаления
        if not messagebox.askyesno("Подтверждение", 
                                  f"Вы действительно хотите удалить оборудование '{equip_name}'?"):
            return
        
        # Удаление оборудования
        success, message = self.db.delete_equipment(equip_id)
        if success:
            messagebox.showinfo("Успех", message)
            self.load_equipment()
        else:
            messagebox.showerror("Ошибка", message)
    
    def load_stats(self):
        """Загрузить статистику"""
        # Статистика оборудования
        equip_stats = self.db.get_equipment_status_stats()
        self.equip_stats_text.delete("1.0", tk.END)
        
        total_equip = 0
        for status, count in equip_stats:
            translated_status = self.equip_status_translation.get(status, status)
            self.equip_stats_text.insert(tk.END, f"{translated_status}: {count} ед.\n")
            total_equip += count
        
        self.equip_stats_text.insert(tk.END, f"\nВсего оборудования: {total_equip} ед.")
        
        # Статистика заявок
        request_stats = self.db.get_request_status_stats()
        self.request_stats_text.delete("1.0", tk.END)
        
        total_requests = 0
        for status, count in request_stats:
            translated_status = self.status_translation.get(status, status)
            self.request_stats_text.insert(tk.END, f"{translated_status}: {count} заявок\n")
            total_requests += count
        
        self.request_stats_text.insert(tk.END, f"\nВсего заявок: {total_requests}")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

class GuestApp:
    """Приложение для гостевого доступа"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.root = tk.Tk()
        self.root.title("LabEquipment Manager - Гостевой доступ")
        self.root.geometry("1300x800")
        self.root.resizable(True, True)  # Разрешаем изменение размера
        self.center_window(1300, 800)
        
        # Словарь для перевода статусов
        self.status_translation = {
            'pending': 'На рассмотрении',
            'approved': 'Одобрено',
            'rejected': 'Отклонено',
            'completed': 'Завершено'
        }
        
        # Словарь для статусов оборудования
        self.equip_status_translation = {
            'available': 'Доступно',
            'in_use': 'В использовании',
            'maintenance': 'На обслуживании'
        }
        
        self.create_widgets()
        self.load_all_requests()
    
    def center_window(self, width, height):
        """Центрировать окно"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """Создание интерфейса гостевого доступа"""
        # Заголовок
        header_frame = tk.Frame(self.root, bg="#607D8B")
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = tk.Label(
            header_frame,
            text="Гостевой доступ (только просмотр)",
            font=("Arial", 14, "bold"),
            bg="#607D8B",
            fg="white",
            padx=20,
            pady=10
        )
        title_label.pack(side="left")
        
        info_label = tk.Label(
            header_frame,
            text="Для редактирования данных войдите в систему",
            font=("Arial", 10),
            bg="#607D8B",
            fg="white",
            padx=20,
            pady=10
        )
        info_label.pack(side="right")
        
        # Панель вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Вкладка 1: Просмотр заявок
        self.create_requests_tab()
        
        # Вкладка 2: Просмотр оборудования
        self.create_equipment_tab()
        
        # Вкладка 3: Статистика
        self.create_stats_tab()
    
    def create_requests_tab(self):
        """Создать вкладку просмотра заявок"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Заявки")
        
        # Контейнер для таблицы
        table_container = tk.Frame(tab)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Таблица всех заявок
        columns = ("ID", "Преподаватель", "Оборудование", "Группа", "Цель", "Дата", "Время", "Статус", "Комментарий")
        self.requests_tree = ttk.Treeview(table_container, columns=columns, show="headings")
        
        # Настройка колонок
        col_widths = [50, 150, 150, 80, 200, 100, 100, 100, 200]
        for col, width in zip(columns, col_widths):
            self.requests_tree.heading(col, text=col)
            self.requests_tree.column(col, width=width, minwidth=50)
        
        # Полосы прокрутки
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.requests_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.requests_tree.xview)
        self.requests_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещение с помощью grid
        self.requests_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Настройка весов для расширения
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Кнопка обновления
        refresh_button = tk.Button(
            tab,
            text="Обновить список",
            font=("Arial", 10),
            command=self.load_all_requests,
            padx=15,
            pady=5
        )
        refresh_button.pack(pady=10)
    
    def create_equipment_tab(self):
        """Создать вкладку просмотра оборудования"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Оборудование")
        
        # Контейнер для таблицы
        table_container = tk.Frame(tab)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Таблица оборудования
        columns = ("ID", "Название", "Описание", "Статус")
        self.equipment_tree = ttk.Treeview(table_container, columns=columns, show="headings")
        
        # Настройка колонок
        col_widths = [50, 200, 300, 100]
        for col, width in zip(columns, col_widths):
            self.equipment_tree.heading(col, text=col)
            self.equipment_tree.column(col, width=width, minwidth=50)
        
        # Полосы прокрутки
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.equipment_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.equipment_tree.xview)
        self.equipment_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещение с помощью grid
        self.equipment_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Настройка весов для расширения
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Кнопка обновления
        refresh_button = tk.Button(
            tab,
            text="Обновить список",
            font=("Arial", 10),
            command=self.load_equipment,
            padx=15,
            pady=5
        )
        refresh_button.pack(pady=10)
        
        # Загрузка оборудования
        self.load_equipment()
    
    def create_stats_tab(self):
        """Создать вкладку со статистикой"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Статистика")
        
        # Фрейм для статистики с прокруткой
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Статистика оборудования
        equip_stats_label = tk.Label(
            scrollable_frame,
            text="Статистика оборудования:",
            font=("Arial", 12, "bold")
        )
        equip_stats_label.grid(row=0, column=0, sticky="w", pady=(20, 10), padx=20)
        
        self.equip_stats_text = tk.Text(scrollable_frame, width=50, height=10, font=("Arial", 10))
        self.equip_stats_text.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        
        # Статистика заявок
        request_stats_label = tk.Label(
            scrollable_frame,
            text="Статистика заявок:",
            font=("Arial", 12, "bold")
        )
        request_stats_label.grid(row=0, column=1, sticky="w", pady=(20, 10), padx=20)
        
        self.request_stats_text = tk.Text(scrollable_frame, width=50, height=10, font=("Arial", 10))
        self.request_stats_text.grid(row=1, column=1, sticky="w", padx=20, pady=(0, 20))
        
        # Кнопка обновления статистики
        refresh_stats_button = tk.Button(
            scrollable_frame,
            text="Обновить статистику",
            font=("Arial", 11),
            command=self.load_stats,
            padx=15,
            pady=5
        )
        refresh_stats_button.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Кнопка выхода
        exit_button = tk.Button(
            scrollable_frame,
            text="Выход",
            font=("Arial", 11),
            command=self.root.destroy,
            padx=15,
            pady=5
        )
        exit_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Упаковка канваса и скроллбара
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Загрузка статистики
        self.load_stats()
    
    def load_all_requests(self):
        """Загрузить все заявки"""
        # Очистить таблицу
        for item in self.requests_tree.get_children():
            self.requests_tree.delete(item)
        
        # Загрузить данные
        requests = self.db.get_all_requests()
        for req in requests:
            # Преобразование статуса
            original_status = req[7]
            translated_status = self.status_translation.get(original_status, original_status)
            
            # Создание новой строки с переведенным статусом
            translated_req = list(req)
            translated_req[7] = translated_status
            
            # Подсветка статуса
            tags = ()
            if original_status == 'approved':
                tags = ('approved',)
            elif original_status == 'rejected':
                tags = ('rejected',)
            elif original_status == 'pending':
                tags = ('pending',)
            elif original_status == 'completed':
                tags = ('completed',)
            
            self.requests_tree.insert("", "end", values=translated_req, tags=tags)
        
        # Настройка цветов
        self.requests_tree.tag_configure('approved', background='#d4edda')
        self.requests_tree.tag_configure('rejected', background='#f8d7da')
        self.requests_tree.tag_configure('pending', background='#fff3cd')
        self.requests_tree.tag_configure('completed', background='#e2e3e5')
    
    def load_equipment(self):
        """Загрузить оборудование"""
        # Очистить таблицу
        for item in self.equipment_tree.get_children():
            self.equipment_tree.delete(item)
        
        # Загрузить данные
        equipment = self.db.get_all_equipment()
        
        for eq in equipment:
            eq_id, name, desc, status = eq
            translated_status = self.equip_status_translation.get(status, status)
            
            # Подсветка статуса
            tags = ()
            if status == 'available':
                tags = ('available',)
            elif status == 'in_use':
                tags = ('in_use',)
            elif status == 'maintenance':
                tags = ('maintenance',)
            
            self.equipment_tree.insert("", "end", 
                                     values=(eq_id, name, desc, translated_status), 
                                     tags=tags)
        
        # Настройка цветов
        self.equipment_tree.tag_configure('available', background='#d4edda')
        self.equipment_tree.tag_configure('in_use', background='#fff3cd')
        self.equipment_tree.tag_configure('maintenance', background='#f8d7da')
    
    def load_stats(self):
        """Загрузить статистику"""
        # Статистика оборудования
        equip_stats = self.db.get_equipment_status_stats()
        self.equip_stats_text.delete("1.0", tk.END)
        
        total_equip = 0
        for status, count in equip_stats:
            translated_status = self.equip_status_translation.get(status, status)
            self.equip_stats_text.insert(tk.END, f"{translated_status}: {count} ед.\n")
            total_equip += count
        
        self.equip_stats_text.insert(tk.END, f"\nВсего оборудования: {total_equip} ед.")
        
        # Статистика заявок
        request_stats = self.db.get_request_status_stats()
        self.request_stats_text.delete("1.0", tk.END)
        
        total_requests = 0
        for status, count in request_stats:
            translated_status = self.status_translation.get(status, status)
            self.request_stats_text.insert(tk.END, f"{translated_status}: {count} заявок\n")
            total_requests += count
        
        self.request_stats_text.insert(tk.END, f"\nВсего заявок: {total_requests}")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

def main():
    """Главная функция"""
    print("Инициализация приложения...")
    
    try:
        # Инициализация базы данных
        db = DatabaseManager()
        
        # Создание главного окна входа
        root = tk.Tk()
        app = LoginWindow(root, db)
        root.mainloop()
        
        # Закрытие БД при выходе
        db.close()
        print("Программа завершена")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        messagebox.showerror("Критическая ошибка", f"Не удалось запустить приложение: {str(e)}")

if __name__ == "__main__":
    print("=" * 50)
    print("LABEQUIPMENT MANAGER v1.0 (Tkinter версия)")
    print("=" * 50)
    main()