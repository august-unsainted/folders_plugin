from typing import Any, Dict

import android_utils
from hook_utils import get_private_field, set_private_field, find_class
from ui.alert import AlertDialogBuilder
from client_utils import get_messages_controller
from base_plugin import BasePlugin, MenuItemData, MenuItemType

from utils import *


__id__ = "folders"
__name__ = "Folders"
__description__ = "Quick edit folders"
__author__ = "@mhidt"
__version__ = "1.0.0"
__icon__ = "exteraPlugins/1"
__min_version__ = "11.12.0"


def log(text: str):
    android_utils.log(f"Folders Plugin:\n{text}")


def is_active(text: str) -> bool:
    return text.startswith("✔️ ")


def reverse_value(text: str) -> str:
    return text.replace("✔️ ", "") if is_active(text) else "✔️ " + text


def sort_folders(folders_names: list[str], folders_ids: list[int]) -> tuple[list[int], list[int]]:
    active, inactive = [], []
    for i in range(len(folders_names)):
        folder_name = folders_names[i]
        folder_id = folders_ids[i]
        if is_active(folder_name):
            active.append(folder_id)
        else:
            inactive.append(folder_id)
    return active, inactive


NotificationCenter = find_class("org.telegram.messenger.NotificationCenter")


class FoldersPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.controller = None
        self.nc = None
        self.folders_names = None
        self.folders_ids = None
        self.folders = None

    def on_plugin_load(self):
        log("Plugin loaded. Adding custom menu items...")
        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.PROFILE_ACTION_MENU,
                text="Log User Info",
                on_click=self.handle_profile_click,
                icon="user_search"  # Example icon
            )
        )
        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.CHAT_ACTION_MENU,
                text="Log User Info",
                on_click=self.handle_profile_click,
                icon="user_search"  # Example icon
            )
        )

    def on_plugin_unload(self):
        log("Plugin unloaded")

    def build_dialog(self, activity, chat_id):
        def on_item_click(bld: AlertDialogBuilder, index: int):
            bld.get_dialog()
            self.folders_names[index] = reverse_value(self.folders_names[index])
            self.build_dialog(activity, chat_id)

        builder = AlertDialogBuilder(activity)
        builder.set_title("Выберите папки")
        builder.set_items(self.folders_names, on_item_click)
        builder.set_negative_button("Отмена", lambda b, w: b.dismiss())
        builder.set_positive_button("Сохранить",
                                    lambda dialog, _, cid=chat_id: self.save_folders(dialog, cid))
        builder.show()

    def handle_profile_click(self, context: Dict[str, Any]):
        fragment = context.get("fragment")
        chat_id = context.get("dialog_id") or context.get("chatId")
        log(f"Message menu item clicked! Chat ID : {chat_id}")
        activity = fragment.getParentActivity()
        if not activity:
            log("Cannot show dialog, no parent activity.")

        raw_folders = get_messages_controller().getDialogFilters().clone()
        ids = []
        names = []
        raw_folders.removeFirst()

        for i in range(raw_folders.size()):
            folder = raw_folders.get(i)
            ids.append(folder.id)
            names.append(folder.name)

        self.folders = raw_folders
        self.folders_ids = ids
        self.folders_names = names
        self.nc = NotificationCenter.getGlobalInstance()
        self.controller = get_messages_controller()
        self.build_dialog(activity, chat_id)

    def save_folders(self, dialog: AlertDialogBuilder, chat_id: int):
        active, inactive = sort_folders(self.folders_names, self.folders_ids)
        log(f"Активные: {active}\nНеактивные: {inactive}")
        log(f"IDs: {self.folders_ids}\nNames: {self.folders_names}\nFolders: {self.folders}")

        for folder_id in active:
            index = self.folders_ids.index(folder_id)
            folder = self.folders.get(index)
            name = folder.name
            always_show = get_private_field(folder, "alwaysShow")
            log(f"Папка {name} до: " + str(always_show))
            if not always_show.contains(chat_id):
                always_show.add(chat_id)
            set_private_field(folder, "alwaysShow", always_show)
            log(f"Папка {name} после: " + str(get_private_field(folder, "alwaysShow")))
            self.controller.deleteDialog(chat_id, 2)
            self.controller.updateFilterDialogs(folder)

        for folder_id in inactive:
            index = self.folders_ids.index(folder_id)
            folder = self.folders.get(index)
            self.controller.updateFilterDialogs(folder)
            always_show = get_private_field(folder, "alwaysShow")
            if always_show.contains(chat_id):
                always_show.remove(always_show.indexOf(chat_id))
                set_private_field(folder, "alwaysShow", always_show)

        self.reload_ui()
        log("Folders saved!")
        dialog.dismiss()

    def reload_ui(self):
        self.nc.postNotificationName(NotificationCenter.dialogFiltersUpdated)
        self.nc.postNotificationName(NotificationCenter.dialogsNeedReload)
