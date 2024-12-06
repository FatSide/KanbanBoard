import customtkinter as ctk
from tkinter import colorchooser
import json
import os
import sys

def resource_path(relative_path):
    """
    Получает абсолютный путь к ресурсу, работающий как из скрипта, так и из .exe.
    Для внешних файлов, таких как JSON, используется директория исполняемого файла.
    """
    try:
        # Если приложение скомпилировано с помощью PyInstaller
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class KanbanApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Настройка окна
        self.title("Kanban Board")
        self.geometry("1300x800")
        ctk.set_appearance_mode("System")  # Light/Dark mode
        ctk.set_default_color_theme("blue")  # Цветовая тема

        # Названия колонок
        self.column_titles = ["Queue", "In Progress", "Review", "Done"]
        # Словарь для хранения колонок (ключ: название, значение: CTkScrollableFrame)
        self.columns = {}

        # Текущий выбранный стикер
        self.selected_sticker = None

        # Путь к файлу для сохранения стикеров
        self.save_file = resource_path("stickers.json")

        # Основной макет
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Создание колонок
        for title in self.column_titles:
            self.create_column(title)

        # Создание фрейма для ввода задачи и кнопок управления
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(side="top", fill="x", padx=20, pady=10)

        # Поле ввода задачи
        self.task_input = ctk.CTkEntry(input_frame, placeholder_text="Enter a new task")
        self.task_input.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)

        # Кнопка добавления задачи
        self.add_task_button = ctk.CTkButton(input_frame, text="+", width=40, height=40, command=self.add_task)
        self.add_task_button.pack(side="left", padx=(0, 10), pady=10)

        # Кнопки перемещения стикера
        self.move_left_button = ctk.CTkButton(input_frame, text="←", width=40, height=40,
                                             command=lambda: self.move_task(-1))
        self.move_left_button.pack(side="left", padx=(0, 5), pady=10)

        self.move_right_button = ctk.CTkButton(input_frame, text="→", width=40, height=40,
                                              command=lambda: self.move_task(1))
        self.move_right_button.pack(side="left", padx=(5, 0), pady=10)

        # Загрузка стикеров из файла при запуске
        self.load_stickers()

    def create_column(self, title):
        """Создает одну колонку для канбан-доски."""
        column_frame = ctk.CTkFrame(self.main_frame, width=250)
        column_frame.pack_propagate(False)  # Отключаем автоматическое изменение размера
        column_frame.pack(side="left", fill="both", expand=True, padx=10)  # фиксированное расстояние между колонками

        # Название колонки
        title_label = ctk.CTkLabel(column_frame, text=title, font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Используем CTkScrollableFrame для вертикальной прокрутки
        tasks_scroll_frame = ctk.CTkScrollableFrame(column_frame, width=250, height=500)
        tasks_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Сохранение ссылки на tasks_scroll_frame, куда будут добавляться стикеры
        self.columns[title] = tasks_scroll_frame

    def add_task(self):
        """Добавляет новую задачу в колонку Queue."""
        task_text = self.task_input.get().strip()
        if task_text:
            self.create_sticker(self.columns["Queue"], text=task_text, bg_color="gray75")
            self.task_input.delete(0, "end")
            self.save_stickers()

    def create_sticker(self, parent_frame, text="", bg_color="gray75"):
        """Создает стикер (задачу) в заданном фрейме."""
        # Изначально рамка совпадает с цветом фона
        sticker = ctk.CTkFrame(parent_frame, corner_radius=8, fg_color=bg_color, border_width=2, border_color=bg_color)
        sticker.pack(pady=5, padx=5, fill="x")

        # Кнопка-карандаш для изменения фона стикера (левый верхний угол)
        edit_button = ctk.CTkButton(sticker, text="🖉", width=30, fg_color="transparent", text_color="black",
                                    command=lambda: self.edit_sticker_bg(sticker))
        edit_button.place(relx=0.0, rely=0.0, x=5, y=5, anchor="nw")

        # Кнопка-крестик для удаления стикера (правый верхний угол)
        delete_button = ctk.CTkButton(sticker, text="✕", width=30, fg_color="transparent", text_color="black",
                                      command=lambda: self.delete_sticker(sticker))
        delete_button.place(relx=1.0, rely=0.0, x=-5, y=5, anchor="ne")

        # Метка с текстом, с переносом строк
        sticker_label = ctk.CTkLabel(sticker, text=text, text_color="black", anchor="w",
                                     wraplength=220, justify="left")
        # Отступ сверху, чтобы текст не перекрывал кнопки
        sticker_label.pack(side="top", fill="both", expand=True, padx=5, pady=(40,5))

        # События для выделения стикера при клике
        sticker.bind("<Button-1>", lambda e: self.select_sticker(sticker))
        sticker_label.bind("<Button-1>", lambda e: self.select_sticker(sticker))

        return sticker

    def select_sticker(self, sticker):
        """Обработчик выбора стикера при клике."""
        # Снимаем выделение с предыдущего стикера, если есть
        if self.selected_sticker is not None and self.selected_sticker != sticker:
            prev_bg = self.selected_sticker.cget("fg_color")
            self.selected_sticker.configure(border_color=prev_bg)

        self.selected_sticker = sticker
        # Выделяем текущий стикер синим контуром
        self.selected_sticker.configure(border_color="blue")

    def move_task(self, direction):
        """Перемещает выбранный стикер в соседнюю колонку."""
        if self.selected_sticker is None:
            return  # Не выбран стикер для перемещения

        # Определяем, в какой колонке сейчас находится стикер
        current_column = None
        for col_name, col_frame in self.columns.items():
            if self.selected_sticker.master == col_frame:
                current_column = col_name
                break

        if current_column is None:
            return

        current_index = self.column_titles.index(current_column)
        target_index = current_index + direction

        # Проверяем, можем ли мы переместиться
        if 0 <= target_index < len(self.column_titles):
            target_column_name = self.column_titles[target_index]
            target_frame = self.columns[target_column_name]

            # Получаем текст и цвет текущего стикера
            # Ищем метку с текстом
            sticker_label = None
            for child in self.selected_sticker.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    sticker_label = child
                    break
            if sticker_label is None:
                return

            task_text = sticker_label.cget("text")
            bg_color = self.selected_sticker.cget("fg_color")

            # Сохраняем ссылку на текущий стикер для удаления
            old_sticker = self.selected_sticker

            # Создаём новый стикер в целевой колонке
            new_sticker = self.create_sticker(target_frame, text=task_text, bg_color=bg_color)

            # Выделяем новый стикер
            self.select_sticker(new_sticker)

            # Удаляем старый стикер
            old_sticker.destroy()

            # Сохраняем изменения
            self.save_stickers()

    def edit_sticker_bg(self, sticker):
        """Редактирование цвета фона стикера."""
        color_code = colorchooser.askcolor(title="Choose background color")
        if color_code and color_code[1]:
            new_bg = color_code[1]
            sticker.configure(fg_color=new_bg)
            # Если этот стикер выбран, оставляем синюю рамку
            if self.selected_sticker == sticker:
                sticker.configure(border_color="blue")
            else:
                # Если не выбран, рамку делаем под цвет фона
                sticker.configure(border_color=new_bg)
            self.save_stickers()

    def delete_sticker(self, sticker):
        """Удаление стикера."""
        if self.selected_sticker == sticker:
            self.selected_sticker = None
        sticker.destroy()
        self.save_stickers()

    def save_stickers(self):
        """Сохраняет текущие стикеры в файл."""
        data = {title: [] for title in self.column_titles}
        for title, col_frame in self.columns.items():
            for sticker in col_frame.winfo_children():
                # Получаем текст и цвет фона стикера
                text = ""
                bg_color = sticker.cget("fg_color")
                for child in sticker.winfo_children():
                    if isinstance(child, ctk.CTkLabel):
                        text = child.cget("text")
                        break
                data[title].append({"text": text, "bg_color": bg_color})
        try:
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving stickers: {e}")

    def load_stickers(self):
        """Загружает стикеры из файла при запуске."""
        if not os.path.exists(self.save_file):
            # Создаем пустой файл, если он не существует
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump({title: [] for title in self.column_titles}, f, ensure_ascii=False, indent=4)
            return  # Файл только что создан, нет стикеров для загрузки

        try:
            with open(self.save_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for title, stickers in data.items():
                if title in self.columns:
                    for sticker_data in stickers:
                        text = sticker_data.get("text", "")
                        bg_color = sticker_data.get("bg_color", "gray75")
                        self.create_sticker(self.columns[title], text=text, bg_color=bg_color)
        except Exception as e:
            print(f"Error loading stickers: {e}")

if __name__ == "__main__":
    app = KanbanApp()
    app.mainloop()
