# kanban_app.py
import customtkinter as ctk
from tkinter import colorchooser
import os
import sys
from typing import Any, Dict, Tuple, List
from kanban_model import KanbanModel

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

# View and Controller
class KanbanApp(ctk.CTk):
    def __init__(self, model: KanbanModel):
        super().__init__()
        self.model = model
        self.model.attach(self.on_model_event)

        # Настройка окна
        self.title("Kanban Board")
        self.geometry("1300x800")
        ctk.set_appearance_mode("System")  # Light/Dark mode
        ctk.set_default_color_theme("blue")  # Цветовая тема

        # Названия колонок
        self.column_titles = model.column_titles
        # Словарь для хранения колонок (ключ: название, значение: ColumnView)
        self.columns: Dict[str, ColumnView] = {}

        # Текущий выбранный стикер
        self.selected_sticker: Tuple[str, int] = (None, None)  # (state, index)

        # Основной макет
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Создание колонок
        for title in self.column_titles:
            column_view = ColumnView(self.main_frame, title, self)
            self.columns[title] = column_view

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
        self.move_left_button = ctk.CTkButton(
            input_frame, text="←", width=40, height=40,
            command=lambda: self.move_task("left")
        )
        self.move_left_button.pack(side="left", padx=(0, 5), pady=10)

        self.move_right_button = ctk.CTkButton(
            input_frame, text="→", width=40, height=40,
            command=lambda: self.move_task("right")
        )
        self.move_right_button.pack(side="left", padx=(5, 0), pady=10)

        # Загрузка стикеров из модели
        self.load_initial_stickers()

    def load_initial_stickers(self):
        """Загружает начальные стикеры из модели."""
        for state, stickers in self.model.columns.items():
            for sticker in stickers:
                self.columns[state].add_sticker_view(sticker["text"], sticker["bg_color"])

    def on_model_event(self, event: str, data: Any):
        """Обработчик событий модели."""
        if event == "add_sticker":
            state = data["state"]
            sticker = data["sticker"]
            self.columns[state].add_sticker_view(sticker["text"], sticker["bg_color"])
        elif event == "delete_sticker":
            state = data["state"]
            index = data["sticker_index"]
            self.columns[state].delete_sticker_view(index)
            # Сбросить выбор, если необходимо
            if self.selected_sticker == (state, index):
                self.selected_sticker = (None, None)
        elif event == "move_sticker":
            # Перестраиваем все колонки
            self.refresh_all_columns()
            self.selected_sticker = (None, None)
        elif event == "edit_sticker_bg":
            state = data["state"]
            index = data["sticker_index"]
            new_bg = data["new_bg"]
            self.columns[state].update_sticker_bg(index, new_bg)
        elif event == "load_stickers":
            self.load_initial_stickers()

    def refresh_all_columns(self):
        """Перестраивает все представления колонок."""
        for column in self.columns.values():
            column.clear_stickers()
        self.load_initial_stickers()

    def add_task(self):
        """Добавляет новую задачу в модель."""
        task_text = self.task_input.get().strip()
        if task_text:
            self.model.add_sticker("Queue", task_text, bg_color="gray75")
            self.task_input.delete(0, "end")

    def select_sticker(self, state: str, index: int):
        """Выбирает стикер."""
        # Снимаем выделение с предыдущего стикера, если есть
        if self.selected_sticker != (None, None):
            prev_state, prev_index = self.selected_sticker
            self.columns[prev_state].deselect_sticker(prev_index)

        # Выделяем новый стикер
        self.selected_sticker = (state, index)
        self.columns[state].select_sticker(index)

    def move_task(self, direction: str):
        """Перемещает выбранный стикер в соседнюю колонку."""
        if self.selected_sticker == (None, None):
            return  # Нет выбранного стикера

        state, index = self.selected_sticker
        self.model.move_sticker(state, index, direction)

    def run(self):
        self.mainloop()

# Column View
class ColumnView(ctk.CTkFrame):
    def __init__(self, parent, title: str, app: KanbanApp):
        super().__init__(parent, width=250)
        self.pack_propagate(False)
        self.pack(side="left", fill="both", expand=True, padx=10)

        self.title = title
        self.app = app

        # Название колонки
        title_label = ctk.CTkLabel(self, text=title, font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Используем CTkScrollableFrame для вертикальной прокрутки
        self.tasks_scroll_frame = ctk.CTkScrollableFrame(self, width=250, height=500)
        self.tasks_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Список для хранения стикеров
        self.stickers: List[StickerView] = []

    def add_sticker_view(self, text: str, bg_color: str):
        """Добавляет представление стикера в колонку."""
        sticker = StickerView(self.tasks_scroll_frame, self.title, len(self.stickers), text, bg_color, self.app)
        self.stickers.append(sticker)
        sticker.pack(pady=5, padx=5, fill="x")

    def delete_sticker_view(self, index: int):
        """Удаляет представление стикера из колонки."""
        if 0 <= index < len(self.stickers):
            sticker = self.stickers.pop(index)
            sticker.destroy()
            # Обновляем индексы оставшихся стикеров
            for i in range(index, len(self.stickers)):
                self.stickers[i].index = i

    def select_sticker(self, index: int):
        """Выделяет стикер по индексу."""
        if 0 <= index < len(self.stickers):
            self.stickers[index].select()

    def deselect_sticker(self, index: int):
        """Снимает выделение стикера по индексу."""
        if 0 <= index < len(self.stickers):
            self.stickers[index].deselect()

    def update_sticker_bg(self, index: int, new_bg: str):
        """Обновляет цвет фона стикера."""
        if 0 <= index < len(self.stickers):
            self.stickers[index].update_bg(new_bg)

    def clear_stickers(self):
        """Удаляет все стикеры из представления."""
        for sticker in self.stickers:
            sticker.destroy()
        self.stickers.clear()

# Sticker View
class StickerView(ctk.CTkFrame):
    def __init__(self, parent, state: str, index: int, text: str, bg_color: str, app: KanbanApp):
        super().__init__(parent, corner_radius=8, fg_color=bg_color, border_width=2, border_color=bg_color)
        self.state = state
        self.index = index
        self.app = app

        # Кнопка-карандаш для изменения фона стикера (левый верхний угол)
        edit_button = ctk.CTkButton(
            self, text="🖉", width=30, fg_color="transparent",
            text_color="black", command=self.edit_bg
        )
        edit_button.place(relx=0.0, rely=0.0, x=5, y=5, anchor="nw")

        # Кнопка-крестик для удаления стикера (правый верхний угол)
        delete_button = ctk.CTkButton(
            self, text="✕", width=30, fg_color="transparent",
            text_color="black", command=self.delete
        )
        delete_button.place(relx=1.0, rely=0.0, x=-5, y=5, anchor="ne")

        # Метка с текстом, с переносом строк
        self.label = ctk.CTkLabel(
            self, text=text, text_color="black", anchor="w",
            wraplength=220, justify="left"
        )
        self.label.pack(side="top", fill="both", expand=True, padx=5, pady=(40,5))

        # События для выделения стикера при клике
        self.bind("<Button-1>", self.on_click)
        self.label.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        """Обработчик клика на стикере."""
        self.app.select_sticker(self.state, self.index)

    def select(self):
        """Выделяет стикер."""
        self.configure(border_color="blue")

    def deselect(self):
        """Снимает выделение стикера."""
        self.configure(border_color=self.cget("fg_color"))

    def edit_bg(self):
        """Редактирует цвет фона стикера."""
        color_code = colorchooser.askcolor(title="Choose background color", initialcolor=self.cget("fg_color"))
        if color_code and color_code[1]:
            new_bg = color_code[1]
            self.configure(fg_color=new_bg, border_color=new_bg)
            self.app.model.edit_sticker_bg(self.state, self.index, new_bg)

    def delete(self):
        """Удаляет стикер."""
        self.app.model.delete_sticker(self.state, self.index)

    def update_bg(self, new_bg: str):
        """Обновляет цвет фона стикера."""
        self.configure(fg_color=new_bg, border_color=new_bg)

# Entry Point
if __name__ == "__main__":
    SAVE_FILE = resource_path("stickers.json")
    COLUMN_TITLES = ["Queue", "In Progress", "Review", "Done"]

    model = KanbanModel(SAVE_FILE, COLUMN_TITLES)
    app = KanbanApp(model)
    app.run()
