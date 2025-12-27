from typing import Any, Dict

import android_utils
from hook_utils import get_private_field, set_private_field, find_class
from ui.alert import AlertDialogBuilder
from client_utils import get_messages_controller
from base_plugin import BasePlugin, MenuItemData, MenuItemType


__id__ = "folders"
__name__ = "Folders"
__description__ = "Quick edit folders"
__author__ = "@mhidt"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"
DialogObject = find_class("org.telegram.messenger.DialogObject")


def log(text: str):
    android_utils.log(f"Folders Plugin:\n{text}")


def is_active(text: str) -> bool:
    return text.startswith("✔️ ")


def reverse_value(text: str) -> str:
    return text.replace("✔️ ", "") if is_active(text) else "✔️ " + text


class FoldersPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.archive = None
        self.controller = None
        self.folders_names = None
        self.folders_ids = None
        self.folders = None

    def on_plugin_load(self):
        log("Plugin loaded. Adding custom menu items...")
        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.PROFILE_ACTION_MENU,
                text="Редактировать папки",
                on_click=self.handle_profile_click,
                icon="user_search"  # Example icon
            )
        )
        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.CHAT_ACTION_MENU,
                text="Редактировать папки",
                on_click=self.handle_profile_click,
                icon="user_search"  # Example icon
            )
        )

    def on_plugin_unload(self):
        log("Plugin unloaded")

    def handle_profile_click(self, context: Dict[str, Any]):
        fragment = context.get("fragment")
        chat = context.get("chatId")
        chat_id = context.get("dialog_id") or (-chat if chat else None) or context.get("userId")
        log(f"Message menu item clicked! Chat ID : {chat_id}")
        activity = fragment.getParentActivity()
        if not activity:
            log("Cannot show dialog, no parent activity.")

        self.controller = get_messages_controller()
        raw_folders = self.controller.getDialogFilters().clone()
        self.archive = raw_folders.removeFirst()

        ids, names = [], []
        for i in range(raw_folders.size()):
            folder = raw_folders.get(i)
            ids.append(folder.id)
            names.append(folder.name)

        self.folders = raw_folders
        self.folders_ids = ids
        self.folders_names = names
        self.load_folders(chat_id)
        self.build_dialog(activity, chat_id)

    def build_dialog(self, activity, chat_id):
        def on_item_click(bld: AlertDialogBuilder, index: int):
            bld.get_dialog()
            self.folders_names[index] = reverse_value(self.folders_names[index])
            self.build_dialog(activity, chat_id)

        builder = AlertDialogBuilder(activity)
        builder.set_title("Выберите папки")
        builder.set_items(self.folders_names, on_item_click)
        builder.set_negative_button("Отмена", lambda b, w: b.dismiss())
        save_func = lambda dialog, _, chat=chat_id: self.save_folders(dialog, chat)
        builder.set_positive_button("Сохранить", save_func)
        builder.show()

    def save_folders(self, dialog: AlertDialogBuilder, chat_id: int):
        for index, folder_id in enumerate(self.folders_ids):
            folder = self.folders.get(index)
            checked = is_active(self.folders_names[index])
            always_show = self.get_dialogs(folder)
            is_contains = always_show.contains(chat_id)
            if checked and not is_contains:
                self.controller.addDialogToFolder(chat_id, 1, -1, 0)
                always_show.add(chat_id)
            elif not checked and is_contains:
                always_show.remove(always_show.indexOf(chat_id))
            set_private_field(folder, "alwaysShow", always_show)
            self.controller.updateFilterDialogs(folder)

        log("Folders saved!")
        dialog.dismiss()

    def load_folders(self, chat_id: int) -> None:
        for i, folder_name in enumerate(self.folders_names):
            folder = self.folders.get(i)
            dialogs = self.get_dialogs(folder)
            if dialogs.contains(chat_id):
                self.folders_names[i] = reverse_value(folder_name)

    @staticmethod
    def get_dialogs(folder):
        return get_private_field(folder, "alwaysShow")
