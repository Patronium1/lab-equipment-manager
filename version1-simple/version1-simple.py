#!/usr/bin/env python3
"""
LabEquipment Manager на Tkinter
"""
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
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
            ORDER BY r.status, r.desired_date
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
    
    def close(self):
        """Закрыть соединение с БД"""
        self.connection.close()

class LoginWindow:
    """Окно входа"""
    
    def __init__(self, root, db_manager):
        self.root = root
        self.db = db_manager
        self.root.title("LabEquipment Manager - Вход")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Центрирование окна
        self.center_window(400, 300)
        
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
        # Заголовок
        title_label = tk.Label(
            self.root, 
            text="Вход в систему",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)
        
        # Фрейм для полей ввода
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=20)
        
        # Логин
        tk.Label(input_frame, text="Логин:", font=("Arial", 11)).grid(
            row=0, column=0, padx=10, pady=10, sticky="e"
        )
        self.username_entry = tk.Entry(input_frame, font=("Arial", 11), width=20)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        
        # Пароль
        tk.Label(input_frame, text="Пароль:", font=("Arial", 11)).grid(
            row=1, column=0, padx=10, pady=10, sticky="e"
        )
        self.password_entry = tk.Entry(
            input_frame, font=("Arial", 11), width=20, show="*"
        )
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)
        
        # Кнопка входа
        login_button = tk.Button(
            self.root, 
            text="Войти", 
            font=("Arial", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=5,
            command=self.login
        )
        login_button.pack(pady=20)
        
        # Подсказка
        hint_label = tk.Label(
            self.root,
            text="Тестовые данные:\nadmin / admin123\nteacher1 / teacher1",
            font=("Arial", 9),
            fg="gray"
        )
        hint_label.pack(pady=10)
        
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

class TeacherApp:
    """Приложение для преподавателя"""
    
    def __init__(self, user_id, full_name, db_manager):
        self.user_id = user_id
        self.full_name = full_name
        self.db = db_manager
        self.root = tk.Tk()
        self.root.title(f"LabEquipment Manager - Преподаватель ({full_name})")
        self.root.geometry("1000x700")
        self.center_window(1000, 700)
        
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
        header_frame.pack(fill="x", pady=(0, 20))
        
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
        
        # Поля формы
        fields_frame = tk.Frame(tab)
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
        self.date_entry.insert(0, "2024-12-20")  # Пример даты
        
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
    
    def create_my_requests_tab(self):
        """Создать вкладку с заявками преподавателя"""
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Мои заявки")
        
        # Таблица заявок
        columns = ("ID", "Оборудование", "Группа", "Цель", "Дата", "Время", "Статус", "Комментарий")
        self.requests_tree = ttk.Treeview(tab, columns=columns, show="headings", height=15)
        
        # Настройка колонок
        col_widths = [50, 150, 80, 200, 100, 100, 100, 150]
        for col, width in zip(columns, col_widths):
            self.requests_tree.heading(col, text=col)
            self.requests_tree.column(col, width=width)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.requests_tree.yview)
        self.requests_tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещение
        self.requests_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
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
            # Подсветка статуса
            tags = ()
            if req[6] == 'approved':
                tags = ('approved',)
            elif req[6] == 'rejected':
                tags = ('rejected',)
            
            self.requests_tree.insert("", "end", values=req, tags=tags)
        
        # Настройка цветов
        self.requests_tree.tag_configure('approved', background='#d4edda')
        self.requests_tree.tag_configure('rejected', background='#f8d7da')
    
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
        self.root.geometry("1200x800")
        self.center_window(1200, 800)
        
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
        header_frame.pack(fill="x", pady=(0, 20))
        
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
        
        # Таблица всех заявок
        columns = ("ID", "Преподаватель", "Оборудование", "Группа", "Цель", "Дата", "Время", "Статус", "Комментарий")
        self.requests_tree = ttk.Treeview(self.root, columns=columns, show="headings", height=20)
        
        # Настройка колонок
        col_widths = [50, 150, 150, 80, 200, 100, 100, 100, 200]
        for col, width in zip(columns, col_widths):
            self.requests_tree.heading(col, text=col)
            self.requests_tree.column(col, width=width)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.requests_tree.yview)
        self.requests_tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещение
        self.requests_tree.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Панель управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Выбор статуса
        tk.Label(control_frame, text="Новый статус:", font=("Arial", 11)).pack(side="left", padx=5)
        self.status_combo = ttk.Combobox(control_frame, values=['pending', 'approved', 'rejected', 'completed'], width=15)
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
        
        exit_button = tk.Button(
            control_frame,
            text="Выход",
            font=("Arial", 11),
            command=self.root.destroy,
            padx=15,
            pady=5
        )
        exit_button.pack(side="right", padx=5)
    
    def load_all_requests(self):
        """Загрузить все заявки"""
        # Очистить таблицу
        for item in self.requests_tree.get_children():
            self.requests_tree.delete(item)
        
        # Загрузить данные
        requests = self.db.get_all_requests()
        for req in requests:
            # Подсветка статуса
            tags = ()
            if req[7] == 'approved':
                tags = ('approved',)
            elif req[7] == 'rejected':
                tags = ('rejected',)
            elif req[7] == 'pending':
                tags = ('pending',)
            
            self.requests_tree.insert("", "end", values=req, tags=tags)
        
        # Настройка цветов
        self.requests_tree.tag_configure('approved', background='#d4edda')
        self.requests_tree.tag_configure('rejected', background='#f8d7da')
        self.requests_tree.tag_configure('pending', background='#fff3cd')
    
    def update_status(self):
        """Обновить статус выбранной заявки"""
        selection = self.requests_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заявку из таблицы")
            return
        
        item = selection[0]
        request_id = self.requests_tree.item(item)['values'][0]
        new_status = self.status_combo.get()
        notes = self.notes_entry.get().strip() or None
        
        try:
            self.db.update_request_status(request_id, new_status, notes)
            messagebox.showinfo("Успех", f"Статус заявки #{request_id} обновлен")
            self.notes_entry.delete(0, tk.END)
            self.load_all_requests()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить статус: {str(e)}")
    
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