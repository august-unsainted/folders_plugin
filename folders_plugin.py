from typing import Any, Dict

import android_utils
from hook_utils import get_private_field, set_private_field, find_class
from ui.alert import AlertDialogBuilder
from client_utils import get_messages_controller
from base_plugin import BasePlugin, MenuItemData, MenuItemType

from android.widget import EditText, FrameLayout, CheckBox, LinearLayout, TextView, Toast, \
    ScrollView, CompoundButton
from android.util import TypedValue
from android.view import View, ViewGroup
from android.content.res import ColorStateList
from org.telegram.ui.ActionBar import Theme

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


VerticalScrollView = find_class("android.widget.VerticalScrollView")


def get_icon_id(icon_name):
    try:
        r_drawable = find_class("org.telegram.messenger.R$drawable")
        field = r_drawable.getField(icon_name)
        return field.get(None)
    except Exception as e:
        print(f"Icon not found: {e}")
        return 0

margin_dp = 20
checkbox_tint_list = ColorStateList(
    [[-16842912], [16842912]],
    [Theme.getColor(Theme.key_dialogTextHint), Theme.getColor(Theme.key_checkboxCheck)])


class FoldersPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.folders_checkboxes = None
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
                icon="msg_folders"
            )
        )
        self.add_menu_item(
            MenuItemData(
                menu_type=MenuItemType.CHAT_ACTION_MENU,
                text="Редактировать папки",
                on_click=self.handle_profile_click,
                icon="msg_folders"
            )
        )

    def on_plugin_unload(self):
        log("Plugin unloaded")

    def handle_profile_click(self, context: Dict[str, Any]):
        fragment = context.get("fragment")
        chat = context.get("chatId")
        chat_id = context.get("dialog_id") or (-chat if chat else None) or context.get("userId")
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
        self.build_dialog(activity, chat_id)

    def build_dialog(self, activity, chat_id):
        builder = AlertDialogBuilder(activity)
        builder.set_title("Выберите папки")
        builder.set_negative_button("Отмена", lambda b, w: b.dismiss())
        save_func = lambda dialog, _, chat=chat_id: self.save_folders(dialog, chat)
        builder.set_positive_button("Сохранить", save_func)
        try:
            builder.set_view(self.generate_view(activity, chat_id))
        except Exception as e:
            log(str(e))
        builder.show()

    def generate_view(self, activity, chat_id):
        view = ScrollView(activity)
        layout = LinearLayout(activity)
        margin_px = int(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, margin_dp,
                                                  activity.getResources().getDisplayMetrics()))
        layout.setOrientation(LinearLayout.VERTICAL)
        layout.setPadding(margin_px, margin_px // 2, margin_px, margin_px // 4)

        self.folders_checkboxes = []
        for i, name in enumerate(self.folders_names):
            checkbox = CheckBox(activity)
            checkbox.setText(name)
            checkbox.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
            checkbox.setButtonTintList(checkbox_tint_list)
            folder = self.folders.get(i)
            if self.is_contains(folder, chat_id)[-1]:
                checkbox.setChecked(True)
            layout.addView(checkbox)
            self.folders_checkboxes.append(checkbox)

        view.addView(layout)
        return view

    def save_folders(self, dialog: AlertDialogBuilder, chat_id: int):
        for index, checkbox in enumerate(self.folders_checkboxes):
            folder = self.folders.get(index)
            dialogs, is_contains = self.is_contains(folder, chat_id)
            checked = checkbox.isChecked()
            if checked and not is_contains:
                self.controller.addDialogToFolder(chat_id, 1, -1, 0)
                dialogs.add(chat_id)
            elif not checked and is_contains:
                dialogs.remove(dialogs.indexOf(chat_id))
            set_private_field(folder, "alwaysShow", dialogs)
            self.controller.updateFilterDialogs(folder)

        log("Folders saved!")
        dialog.dismiss()

    @staticmethod
    def is_contains(folder, chat_id):
        dialogs = get_private_field(folder, "alwaysShow")
        return dialogs, dialogs.contains(chat_id)
