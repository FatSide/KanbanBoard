# kanban_model.py
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List

# Паттерн Observer: Subject
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

# Паттерн State: Абстрактный класс состояния
class State(ABC):
    """Базовый класс состояния задачи."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def move_left(self):
        """Переход в предыдущее состояние."""
        pass

    @abstractmethod
    def move_right(self):
        """Переход в следующее состояние."""
        pass

# Конкретные состояния
class QueueState(State):
    def __init__(self):
        super().__init__("Queue")

    def move_left(self):
        return self  # Нельзя двигаться влево от начального состояния

    def move_right(self):
        return InProgressState()

class InProgressState(State):
    def __init__(self):
        super().__init__("In Progress")

    def move_left(self):
        return QueueState()

    def move_right(self):
        return ReviewState()

class ReviewState(State):
    def __init__(self):
        super().__init__("Review")

    def move_left(self):
        return InProgressState()

    def move_right(self):
        return DoneState()

class DoneState(State):
    def __init__(self):
        super().__init__("Done")

    def move_left(self):
        return ReviewState()

    def move_right(self):
        return self  # Нельзя двигаться вправо от конечного состояния

# Модель данных Kanban
class KanbanModel(Subject):
    def __init__(self, save_file: str, column_titles: List[str]):
        super().__init__()
        self.column_titles = column_titles
        self.save_file = save_file
        self.columns: Dict[str, List[Dict[str, Any]]] = {title: [] for title in column_titles}
        self.state_mapping = {
            "Queue": QueueState,
            "In Progress": InProgressState,
            "Review": ReviewState,
            "Done": DoneState
        }
        self.load_stickers()

    def add_sticker(self, state_name: str, text: str, bg_color: str = "gray75"):
        if state_name in self.columns:
            state_class = self.state_mapping.get(state_name, QueueState)
            state = state_class()
            sticker = {
                "text": text,
                "bg_color": bg_color,
                "state": state.name
            }
            self.columns[state_name].append(sticker)
            self.notify("add_sticker", {"state": state_name, "sticker": sticker})
            self.save_stickers()

    def delete_sticker(self, state_name: str, sticker_index: int):
        if state_name in self.columns and 0 <= sticker_index < len(self.columns[state_name]):
            del self.columns[state_name][sticker_index]
            self.notify("delete_sticker", {"state": state_name, "sticker_index": sticker_index})
            self.save_stickers()

    def move_sticker(self, state_name: str, sticker_index: int, direction: str):
        """Направление: 'left' или 'right'"""
        if state_name not in self.columns:
            return

        if 0 <= sticker_index < len(self.columns[state_name]):
            current_sticker = self.columns[state_name][sticker_index]
            current_state = self.get_state_instance(current_sticker["state"])
            if direction == "left":
                new_state = current_state.move_left()
            elif direction == "right":
                new_state = current_state.move_right()
            else:
                return

            # Удаляем из текущей колонки
            self.columns[state_name].pop(sticker_index)
            # Добавляем в новую колонку
            new_state_name = new_state.name
            new_sticker = {
                "text": current_sticker["text"],
                "bg_color": current_sticker["bg_color"],
                "state": new_state_name
            }
            self.columns[new_state_name].append(new_sticker)
            self.notify("move_sticker", {
                "from_state": state_name,
                "to_state": new_state_name,
                "sticker": new_sticker
            })
            self.save_stickers()

    def edit_sticker_bg(self, state_name: str, sticker_index: int, new_bg: str):
        if state_name in self.columns and 0 <= sticker_index < len(self.columns[state_name]):
            self.columns[state_name][sticker_index]["bg_color"] = new_bg
            self.notify("edit_sticker_bg", {
                "state": state_name,
                "sticker_index": sticker_index,
                "new_bg": new_bg
            })
            self.save_stickers()

    def get_state_instance(self, state_name: str) -> State:
        state_class = self.state_mapping.get(state_name, QueueState)
        return state_class()

    def load_stickers(self):
        if not os.path.exists(self.save_file):
            self.save_stickers()  # Создаем пустой файл
            return
        try:
            with open(self.save_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for state_name, stickers in data.items():
                if state_name in self.columns:
                    for sticker in stickers:
                        # Проверяем валидность состояния
                        state = sticker.get("state", "Queue")
                        if state not in self.state_mapping:
                            sticker["state"] = "Queue"
                        self.columns[state_name].append(sticker)
            self.notify("load_stickers")
        except Exception as e:
            print(f"Error loading stickers: {e}")

    def save_stickers(self):
        try:
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(self.columns, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving stickers: {e}")
