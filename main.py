import customtkinter as ctk
from tkinter import colorchooser
import json
import os
import sys
from typing import Any, Callable, Dict, List, Tuple


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

# Observer Pattern Interfaces
class Subject:
    def __init__(self):
        self._observers: List[Callable[[str, Any], None]] = []

    def attach(self, observer: Callable[[str, Any], None]):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Callable[[str, Any], None]):
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: str, data: Any = None):
        for observer in self._observers:
            observer(event, data)

# Model
class KanbanModel(Subject):
    def __init__(self, save_file: str, column_titles: List[str]):
        super().__init__()
        self.column_titles = column_titles
        self.columns: Dict[str, List[Dict[str, Any]]] = {title: [] for title in column_titles}
        self.save_file = save_file
        self.load_stickers()

    def add_sticker(self, column: str, text: str, bg_color: str = "gray75"):
        if column in self.columns:
            sticker = {"text": text, "bg_color": bg_color}
            self.columns[column].append(sticker)
            self.notify("add_sticker", {"column": column, "sticker": sticker})
            self.save_stickers()

    def delete_sticker(self, column: str, sticker_index: int):
        if column in self.columns and 0 <= sticker_index < len(self.columns[column]):
            del self.columns[column][sticker_index]
            self.notify("delete_sticker", {"column": column, "sticker_index": sticker_index})
            self.save_stickers()

    def move_sticker(self, from_column: str, to_column: str, sticker_index: int):
        if (
            from_column in self.columns and
            to_column in self.columns and
            0 <= sticker_index < len(self.columns[from_column])
        ):
            sticker = self.columns[from_column].pop(sticker_index)
            self.columns[to_column].append(sticker)
            self.notify("move_sticker", {
                "from_column": from_column,
                "to_column": to_column,
                "sticker": sticker
            })
            self.save_stickers()

    def edit_sticker_bg(self, column: str, sticker_index: int, new_bg: str):
        if column in self.columns and 0 <= sticker_index < len(self.columns[column]):
            self.columns[column][sticker_index]["bg_color"] = new_bg
            self.notify("edit_sticker_bg", {
                "column": column,
                "sticker_index": sticker_index,
                "new_bg": new_bg
            })
            self.save_stickers()

    def load_stickers(self):
        if not os.path.exists(self.save_file):
            self.save_stickers()  # Create empty file
            return
        try:
            with open(self.save_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for title, stickers in data.items():
                if title in self.columns:
                    self.columns[title].extend(stickers)
            self.notify("load_stickers")
        except Exception as e:
            print(f"Error loading stickers: {e}")

    def save_stickers(self):
        try:
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(self.columns, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving stickers: {e}")

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
        self.selected_sticker: Tuple[str, int] = (None, None)  # (column, index)

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
            command=lambda: self.move_task(-1)
        )
        self.move_left_button.pack(side="left", padx=(0, 5), pady=10)

        self.move_right_button = ctk.CTkButton(
            input_frame, text="→", width=40, height=40,
            command=lambda: self.move_task(1)
        )
        self.move_right_button.pack(side="left", padx=(5, 0), pady=10)

        # Загрузка стикеров из модели
        self.load_initial_stickers()

    def load_initial_stickers(self):
        """Загружает начальные стикеры из модели."""
        for column, stickers in self.model.columns.items():
            for sticker in stickers:
                self.columns[column].add_sticker_view(sticker["text"], sticker["bg_color"])

    def on_model_event(self, event: str, data: Any):
        """Обработчик событий модели."""
        if event == "add_sticker":
            column = data["column"]
            sticker = data["sticker"]
            self.columns[column].add_sticker_view(sticker["text"], sticker["bg_color"])
        elif event == "delete_sticker":
            column = data["column"]
            index = data["sticker_index"]
            self.columns[column].delete_sticker_view(index)
            # Reset selection if needed
            if self.selected_sticker == (column, index):
                self.selected_sticker = (None, None)
        elif event == "move_sticker":
            # Rebuild all columns
            self.refresh_all_columns()
            self.selected_sticker = (None, None)
        elif event == "edit_sticker_bg":
            column = data["column"]
            index = data["sticker_index"]
            new_bg = data["new_bg"]
            self.columns[column].update_sticker_bg(index, new_bg)
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

    def select_sticker(self, column: str, index: int):
        """Выбирает стикер."""
        # Снимаем выделение с предыдущего стикера, если есть
        if self.selected_sticker != (None, None):
            prev_column, prev_index = self.selected_sticker
            self.columns[prev_column].deselect_sticker(prev_index)

        # Выделяем новый стикер
        self.selected_sticker = (column, index)
        self.columns[column].select_sticker(index)

    def move_task(self, direction: int):
        """Перемещает выбранный стикер в соседнюю колонку."""
        if self.selected_sticker == (None, None):
            return  # Нет выбранного стикера

        column, index = self.selected_sticker
        current_idx = self.column_titles.index(column)
        target_idx = current_idx + direction

        if 0 <= target_idx < len(self.column_titles):
            target_column = self.column_titles[target_idx]
            self.model.move_sticker(column, target_column, index)
            self.selected_sticker = (None, None)

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
    def __init__(self, parent, column: str, index: int, text: str, bg_color: str, app: KanbanApp):
        super().__init__(parent, corner_radius=8, fg_color=bg_color, border_width=2, border_color=bg_color)
        self.column = column
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
        self.app.select_sticker(self.column, self.index)

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
            self.app.model.edit_sticker_bg(self.column, self.index, new_bg)

    def delete(self):
        """Удаляет стикер."""
        self.app.model.delete_sticker(self.column, self.index)

    def update_bg(self, new_bg: str):
        """Обновляет цвет фона стикера."""
        self.configure(fg_color=new_bg, border_color=new_bg)

# Entry Point
if __name__ == "__main__":
    SAVE_FILE = resource_path("stickers.json")
    COLUMN_TITLES = ["Queue", "In Progress", "Review", "Done"]

    model = KanbanModel(SAVE_FILE, COLUMN_TITLES)
    app = KanbanApp(model)
    app.mainloop()
