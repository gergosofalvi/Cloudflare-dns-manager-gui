import kivyapp
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.modalview import ModalView
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty, BooleanProperty
import requests
import os
import json
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.uix.dropdown import DropDown
import sys
from kivy.utils import get_color_from_hex
from kivy.base import EventLoop
import threading
import webbrowser

def get_app_version():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'APP_VERSION.txt'), 'r') as f:
            return f.read().strip()
    except Exception:
        return "0.3.0"  # fallback default

APP_VERSION = get_app_version()
UPDATE_INFO_URL = "https://cfdnsmanager.geri.app/app/osx/update.json"

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"
API_TOKEN_FILE = os.path.join(
    os.path.expanduser("~"),
    "Library", "Application Support", "Cloudflare DNS Manager", "cloudflare_token.json"
)
RECORD_TYPES = [
    "A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "PTR", "CAA", "DNSKEY", "DS", "NAPTR", "SMIMEA", "SSHFP", "TLSA", "URI"
]

# --- Cloudflare színek és glassmorphism stílus ---
CLOUDFLARE_ORANGE = get_color_from_hex("#F38020")
CLOUDFLARE_DARK_BG = get_color_from_hex("#181A20")
CLOUDFLARE_DARKER = get_color_from_hex("#222222")
CLOUDFLARE_LIGHT = get_color_from_hex("#EEEEEE")
CLOUDFLARE_WHITE = get_color_from_hex("#FFFFFF")
GLASS_ALPHA = 0.18  # áttetszőség mértéke

def get_headers(api_token):
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

def verify_token(account_id, api_token):
    url = f"{CLOUDFLARE_API_BASE}/accounts/{account_id}/tokens/verify"
    resp = requests.get(url, headers=get_headers(api_token))
    return resp.ok

def get_zones(api_token):
    all_zones = []
    page = 1
    per_page = 1000
    while True:
        resp = requests.get(
            f"{CLOUDFLARE_API_BASE}/zones",
            headers=get_headers(api_token),
            params={"page": page, "per_page": per_page}
        )
        if not resp.ok:
            break
        data = resp.json()
        all_zones.extend(data["result"])
        info = data.get("result_info", {})
        if info.get("page", 1) >= info.get("total_pages", 1):
            break
        page += 1
    return all_zones

def get_dns_records(api_token, zone_id):
    per_page = 5000  # maximum érték
    resp = requests.get(
        f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records",
        headers=get_headers(api_token),
        params={"page": 1, "per_page": per_page}
    )
    if resp.ok:
        return resp.json()["result"]
    return []

def add_dns_record(api_token, zone_id, record):
    resp = requests.post(f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records", headers=get_headers(api_token), json=record)
    return resp.ok

def update_dns_record(api_token, zone_id, record_id, record):
    resp = requests.put(f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}", headers=get_headers(api_token), json=record)
    return resp.ok

def delete_dns_record(api_token, zone_id, record_id):
    resp = requests.delete(f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}", headers=get_headers(api_token))
    return resp.ok

def purge_cache(api_token, zone_id):
    resp = requests.post(
        f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/purge_cache",
        headers=get_headers(api_token),
        json={"purge_everything": True}
    )
    return resp.ok

def save_window_settings(size, pos):
    data = {}
    # Ensure Application Support/Cloudflare DNS Manager directory exists
    dir_path = os.path.dirname(API_TOKEN_FILE)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    if os.path.exists(API_TOKEN_FILE):
        try:
            with open(API_TOKEN_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["window"] = {"size": size, "pos": pos}
    with open(API_TOKEN_FILE, "w") as f:
        json.dump(data, f)

def load_window_settings():
    if os.path.exists(API_TOKEN_FILE):
        try:
            with open(API_TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("window", None)
        except Exception:
            return None
    return None

def save_accounts(accounts):
    data = {}
    # Ensure Application Support/Cloudflare DNS Manager directory exists
    dir_path = os.path.dirname(API_TOKEN_FILE)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    if os.path.exists(API_TOKEN_FILE):
        try:
            with open(API_TOKEN_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["accounts"] = accounts
    with open(API_TOKEN_FILE, "w") as f:
        json.dump(data, f)

def load_accounts():
    if os.path.exists(API_TOKEN_FILE):
        with open(API_TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("accounts", [])
    return []

# --- Ikon/Resource elérési segédfüggvény ---
def resource_path(filename):
    # PyInstaller/Mac bundle esetén a Resources mappából
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller
        return os.path.join(sys._MEIPASS, filename)
    # Mac app bundle
    bundle_res = os.path.join(os.path.dirname(sys.executable), '..', 'Resources', filename)
    if os.path.exists(bundle_res):
        return bundle_res
    # Fejlesztői futtatás
    return filename

def glassmorphism_background(widget, radius=22, color=CLOUDFLARE_DARK_BG, alpha=GLASS_ALPHA):
    from kivy.graphics import Color, RoundedRectangle
    with widget.canvas.before:
        Color(rgba=(color[0], color[1], color[2], alpha))
        widget._glass_rect = RoundedRectangle(size=widget.size, pos=widget.pos, radius=[radius])
    def update_rect(instance, value):
        widget._glass_rect.size = widget.size
        widget._glass_rect.pos = widget.pos
    widget.bind(size=update_rect, pos=update_rect)

# --- Fő háttér beállítása dark mode-ra ---
Window.clearcolor = CLOUDFLARE_DARK_BG

class LoadingPopup(ModalView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (120, 120)
        self.auto_dismiss = False
        glassmorphism_background(self, radius=32, color=CLOUDFLARE_DARKER, alpha=0.32)
        self.add_widget(Label(text="Loading...", font_size=20, color=CLOUDFLARE_LIGHT))

class DNSManager(BoxLayout):
    error = StringProperty("")
    zones = ListProperty([])
    records = ListProperty([])
    loading = BooleanProperty(False)
    selected_zone_id = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.accounts = load_accounts()
        self.zones = []
        self.records = []
        self.loading_popup = LoadingPopup()
        self.selected_zone_id = ""
        self.selected_account = None
        self.selected_token = None
        self.account_zone_map = {}  # {zone_id: (account, token)}
        if self.accounts:
            self._load_all_zones()
            self.main_ui()
        else:
            self.login_ui()

    def _load_all_zones(self):
        self.zones = []
        self.account_zone_map = {}
        for acc in self.accounts:
            token = acc["token"]
            label = acc.get("label", acc["account_id"])
            zones = get_zones(token)
            for z in zones:
                z_copy = dict(z)
                z_copy["account_id"] = acc["account_id"]
                z_copy["account_label"] = label
                self.zones.append(z_copy)
                self.account_zone_map[z["id"]] = (acc["account_id"], token)

    def login_ui(self):
        self.clear_widgets()
        box = BoxLayout(orientation='vertical', padding=20, spacing=18)
        glassmorphism_background(box, radius=28, color=CLOUDFLARE_DARKER, alpha=0.32)
        box.add_widget(Label(text="Cloudflare Account ID:", color=CLOUDFLARE_LIGHT, font_size=17))
        self.account_id_input = TextInput(multiline=False, background_color=(1,1,1,0.08), foreground_color=CLOUDFLARE_LIGHT, cursor_color=CLOUDFLARE_ORANGE, padding=[12,8,12,8], size_hint_y=None, height=40)
        box.add_widget(self.account_id_input)
        box.add_widget(Label(text="Cloudflare API Token:", color=CLOUDFLARE_LIGHT, font_size=17))
        self.api_token_input = TextInput(password=True, multiline=False, background_color=(1,1,1,0.08), foreground_color=CLOUDFLARE_LIGHT, cursor_color=CLOUDFLARE_ORANGE, padding=[12,8,12,8], size_hint_y=None, height=40)
        box.add_widget(self.api_token_input)
        box.add_widget(Label(text="Account label (e.g. work, personal, ...):", color=CLOUDFLARE_LIGHT, font_size=17))
        self.account_label_input = TextInput(multiline=False, background_color=(1,1,1,0.08), foreground_color=CLOUDFLARE_LIGHT, cursor_color=CLOUDFLARE_ORANGE, padding=[12,8,12,8], size_hint_y=None, height=40)
        box.add_widget(self.account_label_input)
        self.error_label = Label(text=self.error, color=(1,0.2,0.2,1), font_size=15)
        box.add_widget(self.error_label)

        login_btn = Button(
            text="Add account",
            size_hint=(1, None),
            height=44,
            background_normal='',
            background_color=(CLOUDFLARE_ORANGE[0], CLOUDFLARE_ORANGE[1], CLOUDFLARE_ORANGE[2], 0.92),
            color=CLOUDFLARE_WHITE,
            font_size=18
        )
        # Tutorial gomb hozzáadása
        tutorial_btn = Button(
            text="Create Token Tutorial",
            size_hint=(1, None),
            height=38,
            background_normal='',
            background_color=(0.2,0.6,1,1),
            color=CLOUDFLARE_WHITE,
            font_size=15
        )
        tutorial_btn.bind(on_release=self.show_token_tutorial)

        login_btn.bind(on_release=self.try_login)
        login_btn.background_radius = [18]
        box.add_widget(login_btn)
        box.add_widget(tutorial_btn)
        self.add_widget(box)

    def try_login(self, instance):
        acc_id = self.account_id_input.text.strip()
        token = self.api_token_input.text.strip()
        label = self.account_label_input.text.strip()
        self.show_loading()
        Clock.schedule_once(lambda dt: self._do_login(acc_id, token, label), 0.1)

    def _do_login(self, acc_id, token, label):
        if not verify_token(acc_id, token):
            self.hide_loading()
            self.error_label.text = "Invalid Account ID or API token!"
            return
        if not label:
            self.hide_loading()
            self.error_label.text = "Label is required!"
            return
        for acc in self.accounts:
            if acc["account_id"] == acc_id:
                self.hide_loading()
                self.error_label.text = "This account is already added!"
                return
        self.accounts.append({"account_id": acc_id, "token": token, "label": label})
        save_accounts(self.accounts)
        self._load_all_zones()
        self.main_ui()
        self.hide_loading()

    def main_ui(self):
        self.clear_widgets()
        root = BoxLayout(orientation='vertical', padding=[dp(20), dp(20), dp(20), dp(20)], spacing=18)
        glassmorphism_background(root, radius=32, color=CLOUDFLARE_DARKER, alpha=0.28)
        search_row = BoxLayout(orientation='vertical', size_hint=(1, None), height=54, spacing=0)
        glassmorphism_background(search_row, radius=18, color=CLOUDFLARE_DARK_BG, alpha=0.22)
        search_label = Label(text="Search:", font_size=16, color=CLOUDFLARE_LIGHT, size_hint=(None, None), size=(90, 24))
        search_row.add_widget(search_label)
        self.domain_search_input = TextInput(
            hint_text="Domain or account name...",
            multiline=False,
            size_hint=(1, None),
            height=38,
            font_size=16,
            background_color=(1,1,1,0.10),
            foreground_color=CLOUDFLARE_LIGHT,
            cursor_color=CLOUDFLARE_ORANGE,
            padding=[12,8,12,8]
        )
        self.domain_search_input.bind(focus=self._on_search_focus)
        self.domain_search_input.bind(text=self._on_domain_search)
        search_row.add_widget(self.domain_search_input)
        self._build_domain_dropdown()
        root.add_widget(search_row)
        self.error_label = Label(text=self.error, color=(1,0.2,0.2,1), font_size=16, size_hint=(1, None), height=30)
        root.add_widget(self.error_label)
        header_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50, spacing=10)
        glassmorphism_background(header_row, radius=18, color=CLOUDFLARE_DARK_BG, alpha=0.22)
        cache_btn = Button(
            text="Clear cache",
            size_hint=(None, None),
            size=(100, 44),
            background_normal='',
            background_color=(0.25,0.25,0.35,0.85),
            color=CLOUDFLARE_LIGHT,
            font_size=16
        )
        cache_btn.background_radius = [16]
        cache_btn.bind(on_release=self.cache_clear)
        header_row.add_widget(cache_btn)
        add_btn = Button(
            text="Add record",
            size_hint=(None, None),
            size=(90, 44),
            background_normal='',
            background_color=(CLOUDFLARE_ORANGE[0], CLOUDFLARE_ORANGE[1], CLOUDFLARE_ORANGE[2], 0.92),
            color=CLOUDFLARE_WHITE,
            font_size=16
        )
        add_btn.background_radius = [16]
        add_btn.bind(on_release=self.add_record)
        header_row.add_widget(add_btn)
        settings_btn = Button(
            size_hint=(None, None),
            size=(85, 44),
            background_normal='',
            background_color=(0.2,0.2,0.25,0.85),
            text='settings',
            font_size=16,
            color=CLOUDFLARE_LIGHT
        )
        settings_btn.background_radius = [16]
        settings_btn.bind(on_release=self.open_settings_popup)
        header_row.add_widget(settings_btn)
        root.add_widget(header_row)
        record_search_row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=38, spacing=8)
        glassmorphism_background(record_search_row, radius=14, color=CLOUDFLARE_DARK_BG, alpha=0.18)
        record_search_label = Label(text="Record search:", font_size=15, color=CLOUDFLARE_LIGHT, size_hint=(None, None), size=(120, 38))
        self.record_search_input = TextInput(
            hint_text="Name or content...",
            multiline=False,
            size_hint=(1, None),
            height=32,
            font_size=15,
            background_color=(1,1,1,0.10),
            foreground_color=CLOUDFLARE_LIGHT,
            cursor_color=CLOUDFLARE_ORANGE,
            padding=[12,8,12,8]
        )
        self.record_search_input.bind(text=self._on_record_search)
        record_search_row.add_widget(record_search_label)
        record_search_row.add_widget(self.record_search_input)
        root.add_widget(record_search_row)
        table_section = BoxLayout(orientation='vertical', size_hint=(1, 1), padding=[0, 0, 0, 0])
        glassmorphism_background(table_section, radius=24, color=CLOUDFLARE_DARK_BG, alpha=0.22)
        with table_section.canvas.before:
            Color(0.13,0.14,0.18,1)
            self._table_rect = Rectangle(size=table_section.size, pos=table_section.pos)
        def update_rect(instance, value):
            self._table_rect.size = table_section.size
            self._table_rect.pos = table_section.pos
        table_section.bind(size=update_rect, pos=update_rect)
        self.col_ratios = [0.09, 0.22, 0.27, 0.09, 0.09, 0.09, 0.09]  # 7 oszlop, összesen 1.0
        self.records_grid = GridLayout(cols=7, size_hint_y=None, row_default_height=48, spacing=2, padding=[0,0,0,0], size_hint_x=1)
        self.records_grid.bind(minimum_height=self.records_grid.setter('height'))
        self.scroll = ScrollView(size_hint=(1, 1), bar_width=8, scroll_type=['bars', 'content'])
        self.scroll.add_widget(self.records_grid)
        table_section.add_widget(self.scroll)
        root.add_widget(table_section)
        self.add_widget(root)
        Window.bind(on_resize=self._on_window_resize)
        self._on_window_resize(Window, Window.width, Window.height)

    def _on_window_resize(self, window, width, height):
        # Frissítsd a táblázatot, hogy az oszlopok arányosan igazodjanak az ablakhoz
        self.refresh_records_grid()

    def _truncate(self, text, maxlen=25):
        if text is None:
            return ""
        if len(text) > maxlen:
            return text[:maxlen-3] + "..."
        return text

    def refresh_records_grid(self):
        from kivy.core.window import Window
        self.records_grid.clear_widgets()
        headers = ["Type", "Name", "Content", "TTL", "Proxy", "edit", "del"]
        total_width = Window.width - 2*20  # padding
        col_ratios = [0.09, 0.22, 0.27, 0.09, 0.09, 0.09, 0.09]
        col_widths = [int(r*total_width) for r in col_ratios]
        from kivy.graphics import Color, Rectangle
        def bind_rect(widget):
            def update_rect(instance, value):
                widget._rect.size = widget.size
                widget._rect.pos = widget.pos
            widget.bind(size=update_rect, pos=update_rect)
        # Header sor vissza
        for i, h in enumerate(headers):
            header_label = Label(text=h, bold=True, font_size=16, color=(0.95,0.95,0.98,1), size_hint_x=None, width=col_widths[i], size_hint_y=None, height=48)
            with header_label.canvas.before:
                Color(0.18,0.19,0.23,1)
                header_label._rect = Rectangle(size=header_label.size, pos=header_label.pos)
            bind_rect(header_label)
            self.records_grid.add_widget(header_label)
        # Szűrés a rekord kereső alapján
        filter_text = self.record_search_input.text.lower() if hasattr(self, 'record_search_input') else ''
        filtered_records = [rec for rec in self.records if filter_text in rec['name'].lower() or filter_text in rec['content'].lower()]
        # Sorok
        for idx, rec in enumerate(filtered_records):
            row_color = (0.13,0.14,0.18,1)
            # Típus
            type_label = Label(text=rec["type"], font_size=16, color=(0.95,0.95,0.98,1), size_hint_x=None, width=col_widths[0], size_hint_y=None, height=48)
            with type_label.canvas.before:
                Color(*row_color)
                type_label._rect = Rectangle(size=type_label.size, pos=type_label.pos)
            bind_rect(type_label)
            self.records_grid.add_widget(type_label)
            # Név
            name_val = self._truncate(rec["name"])
            name_label = Label(text=name_val, font_size=16, color=(0.95,0.95,0.98,1), size_hint_x=None, width=col_widths[1], size_hint_y=None, height=48)
            if len(rec["name"]) > 25:
                name_label.halign = 'left'
                name_label.tooltip = rec["name"]
            with name_label.canvas.before:
                Color(*row_color)
                name_label._rect = Rectangle(size=name_label.size, pos=name_label.pos)
            bind_rect(name_label)
            self.records_grid.add_widget(name_label)
            # Tartalom
            content_val = self._truncate(rec["content"])
            content_label = Label(text=content_val, font_size=16, color=(0.95,0.95,0.98,1), size_hint_x=None, width=col_widths[2], size_hint_y=None, height=48)
            if len(rec["content"]) > 25:
                content_label.halign = 'left'
                content_label.tooltip = rec["content"]
            with content_label.canvas.before:
                Color(*row_color)
                content_label._rect = Rectangle(size=content_label.size, pos=content_label.pos)
            bind_rect(content_label)
            self.records_grid.add_widget(content_label)
            # TTL
            ttl_val = self._truncate(str(rec["ttl"]))
            ttl_label = Label(text=ttl_val, font_size=16, color=(0.95,0.95,0.98,1), size_hint_x=None, width=col_widths[3], size_hint_y=None, height=48)
            if len(str(rec["ttl"])) > 25:
                ttl_label.halign = 'left'
                ttl_label.tooltip = str(rec["ttl"])
            with ttl_label.canvas.before:
                Color(*row_color)
                ttl_label._rect = Rectangle(size=ttl_label.size, pos=ttl_label.pos)
            bind_rect(ttl_label)
            self.records_grid.add_widget(ttl_label)
            # Proxy ikon PNG-vel
            if rec.get("proxied"):
                proxy_widget = Image(source=resource_path("Cloudflare32px.png"), size_hint_x=None, width=col_widths[4], size_hint_y=None, height=32)
            else:
                proxy_widget = Image(source=resource_path("Cloudflare32px_gray.png"), size_hint_x=None, width=col_widths[4], size_hint_y=None, height=32)
            self.records_grid.add_widget(proxy_widget)
            # Szerkesztés gomb
            edit_btn = Button(size_hint=(None, None), size=(60, 40), background_normal='', background_color=(0.2,0.6,1,1), text='edit', font_size=18, color=(1,1,1,1), width=col_widths[5], height=48)
            with edit_btn.canvas.before:
                Color(*row_color)
                edit_btn._rect = Rectangle(size=edit_btn.size, pos=edit_btn.pos)
            bind_rect(edit_btn)
            edit_btn.bind(on_release=lambda inst, r=rec: self.edit_record(r))
            self.records_grid.add_widget(edit_btn)
            # Törlés gomb
            del_btn = Button(size_hint=(None, None), size=(60, 40), background_normal='', background_color=(1,0.3,0.3,1), text='del', font_size=18, color=(1,1,1,1), width=col_widths[6], height=48)
            with del_btn.canvas.before:
                Color(*row_color)
                del_btn._rect = Rectangle(size=del_btn.size, pos=del_btn.pos)
            bind_rect(del_btn)
            del_btn.bind(on_release=lambda inst, r=rec: self.delete_record(r))
            self.records_grid.add_widget(del_btn)

    def edit_record(self, rec):
        from kivy.core.window import Window
        popup_width = max(350, min(700, int(Window.width * 0.8)))
        popup = Popup(title="Edit DNS record", size_hint=(None, None), size=(popup_width, 640), auto_dismiss=False)
        from kivy.uix.scrollview import ScrollView
        layout = BoxLayout(orientation='vertical', padding=20, spacing=12, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        type_spinner = Spinner(text=rec["type"], values=RECORD_TYPES, size_hint=(1, None), height=40, font_size=15)
        name_input = TextInput(text=rec["name"], multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        content_input = TextInput(text=rec["content"], multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        ttl_input = TextInput(text=str(rec["ttl"]), multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        from kivy.uix.togglebutton import ToggleButton
        proxy_toggle = ToggleButton(text="Cloudflare proxy: ON" if rec.get("proxied") else "Cloudflare proxy: OFF", state="down" if rec.get("proxied") else "normal", size_hint=(1, None), height=40, background_normal='', background_color=(1,0.5,0,1) if rec.get("proxied") else (.3,.3,.3,1), font_size=15)
        def on_toggle(instance):
            if instance.state == "down":
                instance.text = "Cloudflare proxy: ON"
                instance.background_color = (1,0.5,0,1)
            else:
                instance.text = "Cloudflare proxy: OFF"
                instance.background_color = (.3,.3,.3,1)
        proxy_toggle.bind(on_press=on_toggle)
        error_label = Label(text="", color=(1,0,0,1), font_size=14, size_hint=(1, None), height=24)
        def on_save(instance):
            record = {
                "type": type_spinner.text,
                "name": name_input.text.strip(),
                "content": content_input.text.strip(),
                "ttl": int(ttl_input.text.strip() or 3600),
                "proxied": proxy_toggle.state == "down"
            }
            if not record["name"] or not record["content"]:
                error_label.text = "Name and content are required!"
                return
            if update_dns_record(self.selected_token, self.selected_zone_id, rec["id"], record):
                popup.dismiss()
                self.load_records()
                self.show_toast("Record updated", success=True)
            else:
                error_label.text = "Error updating record!"
                self.show_toast("Error updating record!", success=False)
        save_btn = Button(text="Save", size_hint=(1, None), height=40, background_color=(0.2,0.6,1,1), color=(1,1,1,1), font_size=15)
        save_btn.bind(on_release=on_save)
        cancel_btn = Button(text="Cancel", size_hint=(1, None), height=40, background_color=(.7,.7,.7,1), font_size=15)
        cancel_btn.bind(on_release=lambda i: popup.dismiss())
        layout.add_widget(Label(text="Type:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(type_spinner)
        layout.add_widget(Label(text="Name:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(name_input)
        layout.add_widget(Label(text="Content:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(content_input)
        layout.add_widget(Label(text="TTL:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(ttl_input)
        layout.add_widget(proxy_toggle)
        layout.add_widget(error_label)
        layout.add_widget(save_btn)
        layout.add_widget(cancel_btn)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        scroll.add_widget(layout)
        popup.content = scroll
        popup.open()

    def delete_record(self, rec):
        self.show_loading()
        Clock.schedule_once(lambda dt: self._do_delete_record(rec), 0.1)

    def _do_delete_record(self, rec):
        ok = delete_dns_record(self.selected_token, self.selected_zone_id, rec["id"])
        self.load_records()
        self.hide_loading()
        if ok:
            self.show_toast("Record deleted", success=True)
        else:
            self.show_toast("Error deleting record", success=False)

    def add_record(self, instance):
        from kivy.core.window import Window
        popup_width = max(350, min(700, int(Window.width * 0.8)))
        popup = Popup(title="Add new DNS record", size_hint=(None, None), size=(popup_width, 640), auto_dismiss=False)
        from kivy.uix.scrollview import ScrollView
        layout = BoxLayout(orientation='vertical', padding=20, spacing=12, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        type_spinner = Spinner(text="A", values=RECORD_TYPES, size_hint=(1, None), height=40, font_size=15)
        name_input = TextInput(hint_text="Name", multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        content_input = TextInput(hint_text="Content", multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        ttl_input = TextInput(hint_text="TTL", text="3600", multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        from kivy.uix.togglebutton import ToggleButton
        proxy_toggle = ToggleButton(text="Cloudflare proxy: OFF", state="normal", size_hint=(1, None), height=40, background_normal='', background_color=(.3,.3,.3,1), font_size=15)
        def on_toggle(instance):
            if instance.state == "down":
                instance.text = "Cloudflare proxy: ON"
                instance.background_color = (1,0.5,0,1)
            else:
                instance.text = "Cloudflare proxy: OFF"
                instance.background_color = (.3,.3,.3,1)
        proxy_toggle.bind(on_press=on_toggle)
        error_label = Label(text="", color=(1,0,0,1), font_size=14, size_hint=(1, None), height=24)
        def on_save(instance):
            record = {
                "type": type_spinner.text,
                "name": name_input.text.strip(),
                "content": content_input.text.strip(),
                "ttl": int(ttl_input.text.strip() or 3600),
                "proxied": proxy_toggle.state == "down"
            }
            if not record["name"] or not record["content"]:
                error_label.text = "Name and content are required!"
                return
            if add_dns_record(self.selected_token, self.selected_zone_id, record):
                popup.dismiss()
                self.load_records()
                self.show_toast("Record added", success=True)
            else:
                error_label.text = "Error adding record!"
                self.show_toast("Error adding record!", success=False)
        save_btn = Button(text="Add", size_hint=(1, None), height=40, background_color=(0.2,0.6,1,1), color=(1,1,1,1), font_size=15)
        save_btn.bind(on_release=on_save)
        cancel_btn = Button(text="Cancel", size_hint=(1, None), height=40, background_color=(.7,.7,.7,1), font_size=15)
        cancel_btn.bind(on_release=lambda i: popup.dismiss())
        layout.add_widget(Label(text="Type:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(type_spinner)
        layout.add_widget(Label(text="Name:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(name_input)
        layout.add_widget(Label(text="Content:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(content_input)
        layout.add_widget(Label(text="TTL:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(ttl_input)
        layout.add_widget(proxy_toggle)
        layout.add_widget(error_label)
        layout.add_widget(save_btn)
        layout.add_widget(cancel_btn)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        scroll.add_widget(layout)
        popup.content = scroll
        popup.open()

    def cache_clear(self, instance):
        self.show_loading()
        Clock.schedule_once(lambda dt: self._do_cache_clear(), 0.1)

    def _do_cache_clear(self):
        ok = purge_cache(self.selected_token, self.selected_zone_id)
        self.hide_loading()
        if ok:
            self.show_toast("Success: cache cleared", success=True)
        else:
            self.show_toast("Error: cache clear failed", success=False)

    def show_loading(self):
        self.loading_popup.open()

    def hide_loading(self):
        self.loading_popup.dismiss()

    def open_settings_popup(self, instance):
        from kivy.core.window import Window
        popup_width = max(350, min(700, int(Window.width * 0.8)))
        popup = Popup(title="Manage Cloudflare accounts", size_hint=(None, None), size=(popup_width, 650), auto_dismiss=False)
        from kivy.uix.scrollview import ScrollView
        layout = BoxLayout(orientation='vertical', padding=16, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        self.add_account_fields_visible = False
        self._settings_popup_refresh(layout, popup)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        scroll.add_widget(layout)
        popup.content = scroll
        popup.open()

    def _settings_popup_refresh(self, layout, popup):
        layout.clear_widgets()
        from kivy.uix.button import Button
        from kivy.uix.textinput import TextInput
        from kivy.uix.label import Label
        from kivy.uix.boxlayout import BoxLayout
        # Header row
        header = BoxLayout(orientation='horizontal', size_hint=(1, None), height=30, spacing=8, padding=[0,0,0,0])
        header.add_widget(Label(text="Label", font_size=16, bold=True, size_hint=(0.4, None), height=30))
        header.add_widget(Label(text="Account ID", font_size=16, bold=True, size_hint=(0.4, None), height=30))
        header.add_widget(Label(text="Actions", font_size=16, bold=True, size_hint=(0.2, None), height=30))
        layout.add_widget(header)

        # Account rows
        for idx, acc in enumerate(self.accounts):
            row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=32, spacing=8, padding=[0,0,0,0])
            acc_label = Label(text=acc.get('label', acc['account_id']), font_size=14, size_hint=(0.4, None), height=32)
            acc_id = Label(text=acc.get('account_id', ''), font_size=14, size_hint=(0.4, None), height=32)
            actions = BoxLayout(orientation='horizontal', size_hint=(0.2, None), height=32, spacing=4)
            edit_btn = Button(size_hint=(None, None), size=(50, 28), background_normal='', background_color=(0.2,0.6,1,1), text='edit', font_size=14, color=(1,1,1,1))
            edit_btn.bind(on_release=lambda inst, i=idx: self._edit_account_popup(i, layout, popup))
            del_btn = Button(size_hint=(None, None), size=(50, 28), background_normal='', background_color=(1,0.3,0.3,1), text='del', font_size=14, color=(1,1,1,1))
            def make_del(acc_id):
                return lambda inst: self._delete_account_and_refresh(acc_id, layout, popup)
            del_btn.bind(on_release=make_del(acc['account_id']))
            actions.add_widget(edit_btn)
            actions.add_widget(del_btn)
            row.add_widget(acc_label)
            row.add_widget(acc_id)
            row.add_widget(actions)
            layout.add_widget(row)
        # Add button
        add_btn = Button(size_hint=(None, None), size=(80, 32), background_normal='', background_color=(0.2,0.6,1,1), text='add', font_size=15, color=(1,1,1,1))
        def on_add(inst):
            self.add_account_fields_visible = True
            self._settings_popup_refresh(layout, popup)
        add_btn.bind(on_release=on_add)
        layout.add_widget(add_btn)
        # Tutorial gomb hozzáadása a header után
        tutorial_btn = Button(
            text="Create Token Tutorial",
            size_hint=(1, None),
            height=32,
            background_normal='',
            background_color=(0.2,0.6,1,1),
            color=CLOUDFLARE_WHITE,
            font_size=15
        )
        tutorial_btn.bind(on_release=self.show_token_tutorial)
        layout.add_widget(tutorial_btn)
        # About/info gomb
        about_btn = Button(text="About / Info", size_hint=(1, None), height=32, background_color=(0.2,0.6,1,1), color=CLOUDFLARE_WHITE, font_size=15)
        about_btn.bind(on_release=self.show_about_popup)
        layout.add_widget(about_btn)
        # Add account fields
        if getattr(self, 'add_account_fields_visible', False):
            acc_id_input = TextInput(hint_text="Account ID", multiline=False, size_hint=(1, None), height=36, font_size=15)
            token_input = TextInput(hint_text="API Token", multiline=False, password=True, size_hint=(1, None), height=36, font_size=15)
            label_input = TextInput(hint_text="Account label (e.g. work, personal, ...)", multiline=False, size_hint=(1, None), height=36, font_size=15)
            error_label = Label(text="", color=(1,0,0,1), font_size=14, size_hint=(1, None), height=20)
            def on_save(instance):
                acc_id = acc_id_input.text.strip()
                token = token_input.text.strip()
                label = label_input.text.strip()
                if not acc_id or not token or not label:
                    error_label.text = "Account ID, API token and label are required!"
                    return
                if not verify_token(acc_id, token):
                    error_label.text = "Invalid Account ID or API token!"
                    return
                for acc in self.accounts:
                    if acc["account_id"] == acc_id:
                        error_label.text = "This account is already added!"
                        return
                self.accounts.append({"account_id": acc_id, "token": token, "label": label})
                save_accounts(self.accounts)
                self._load_all_zones()
                self.main_ui()
                popup.dismiss()
            save_btn = Button(text="Save", size_hint=(1, None), height=36, background_color=(0.2,0.6,1,1), color=(1,1,1,1), font_size=15)
            save_btn.bind(on_release=on_save)
            cancel_btn = Button(text="Cancel", size_hint=(1, None), height=36, background_color=(.7,.7,.7,1), font_size=15)
            def on_cancel(inst):
                self.add_account_fields_visible = False
                self._settings_popup_refresh(layout, popup)
            cancel_btn.bind(on_release=on_cancel)
            layout.add_widget(acc_id_input)
            layout.add_widget(token_input)
            layout.add_widget(label_input)
            layout.add_widget(error_label)
            layout.add_widget(save_btn)
            layout.add_widget(cancel_btn)
        close_btn = Button(text="Close", size_hint=(1, None), height=36, background_color=(.7,.7,.7,1), font_size=15)
        close_btn.bind(on_release=lambda i: popup.dismiss())
        # Frissítés ellenőrző gomb
        update_btn = Button(text="Check for updates", size_hint=(1, None), height=36, background_color=(0.2,0.6,1,1), color=CLOUDFLARE_WHITE, font_size=15)
        update_btn.bind(on_release=lambda i: self.check_for_update())
        layout.add_widget(update_btn)
        layout.add_widget(close_btn)

    def _delete_account_and_refresh(self, acc_id, layout, popup):
        self.accounts = [a for a in self.accounts if a["account_id"] != acc_id]
        save_accounts(self.accounts)
        self._load_all_zones()
        self.main_ui()
        self._settings_popup_refresh(layout, popup)

    def _edit_account_popup(self, idx, parent_layout, parent_popup):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.textinput import TextInput
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        acc = self.accounts[idx]
        from kivy.core.window import Window
        popup_width = max(350, min(700, int(Window.width * 0.8)))
        popup = Popup(title="Edit account", size_hint=(None, None), size=(popup_width, 500), auto_dismiss=False)
        from kivy.uix.scrollview import ScrollView
        layout = BoxLayout(orientation='vertical', padding=20, spacing=12, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        label_input = TextInput(text=acc.get('label',''), hint_text="Account label", multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        acc_id_input = TextInput(text=acc.get('account_id',''), hint_text="Account ID", multiline=False, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        token_input = TextInput(text=acc.get('token',''), hint_text="API Token", multiline=False, password=True, size_hint=(1, None), height=40, font_size=15, padding=[8,8,8,8])
        error_label = Label(text="", color=(1,0,0,1), font_size=14, size_hint=(1, None), height=24)
        def on_save(instance):
            label = label_input.text.strip()
            acc_id = acc_id_input.text.strip()
            token = token_input.text.strip()
            if not label or not acc_id or not token:
                error_label.text = "All fields are required!"
                return
            # Ellenőrizzük, hogy másik account_id már létezik-e
            for i, a in enumerate(self.accounts):
                if i != idx and a["account_id"] == acc_id:
                    error_label.text = "This account ID is already used!"
                    return
            self.accounts[idx]['label'] = label
            self.accounts[idx]['account_id'] = acc_id
            self.accounts[idx]['token'] = token
            save_accounts(self.accounts)
            self._load_all_zones()
            self.main_ui()
            parent_popup.dismiss()
        save_btn = Button(text="Save", size_hint=(1, None), height=40, background_color=(0.2,0.6,1,1), color=(1,1,1,1), font_size=15)
        save_btn.bind(on_release=on_save)
        cancel_btn = Button(text="Cancel", size_hint=(1, None), height=40, background_color=(.7,.7,.7,1), font_size=15)
        cancel_btn.bind(on_release=lambda i: popup.dismiss())
        layout.add_widget(Label(text="Account label:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(label_input)
        layout.add_widget(Label(text="Account ID:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(acc_id_input)
        layout.add_widget(Label(text="API Token:", font_size=14, size_hint=(1, None), height=24))
        layout.add_widget(token_input)
        layout.add_widget(error_label)
        layout.add_widget(save_btn)
        layout.add_widget(cancel_btn)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        scroll.add_widget(layout)
        popup.content = scroll
        popup.open()

    def _build_domain_dropdown(self):
        # Létrehozza vagy frissíti a dropdown-t a kereső alatt
        if hasattr(self, 'domain_dropdown') and self.domain_dropdown:
            self.domain_dropdown.dismiss()
        self.domain_dropdown = DropDown(auto_width=False, width=400, max_height=600)
        self._update_domain_dropdown()
        self.domain_search_input.unbind(on_text_validate=self._on_domain_dropdown_select)
        self.domain_search_input.bind(on_text_validate=self._on_domain_dropdown_select)

    def _update_domain_dropdown(self):
        self.domain_dropdown.clear_widgets()
        filter_text = self.domain_search_input.text.lower()
        filtered = [z for z in self.zones if filter_text in z['name'].lower() or filter_text in z.get('account_label','').lower()]
        for z in filtered:
            label = f"{z['name']} ({z.get('account_label',z['account_id'])})"
            btn = Button(text=label, size_hint_y=None, height=36, halign='left', valign='middle', background_normal='', background_color=(.18,.19,.23,1), color=(.95,.95,.98,1))
            btn.bind(on_release=lambda btn, l=label: self._on_domain_dropdown_select(btn, l))
            self.domain_dropdown.add_widget(btn)
        if not filtered:
            btn = Button(text="No results", size_hint_y=None, height=36, background_normal='', background_color=(.3,.3,.3,1), color=(1,1,1,1), disabled=True)
            self.domain_dropdown.add_widget(btn)

    def _on_search_focus(self, instance, value):
        if value:
            # Csak akkor töröljük, ha tényleg egy domain volt kiválasztva (tehát a szöveg pontosan egyezik egy domain label-lel)
            current = self.domain_search_input.text
            found = False
            for z in self.zones:
                l = f"{z['name']} ({z.get('account_label',z['account_id'])})"
                if l == current:
                    found = True
                    break
            if found:
                self.domain_search_input.text = ''
            self._update_domain_dropdown()
            if not self.domain_dropdown.attach_to:
                self.domain_dropdown.open(self.domain_search_input)
        else:
            if self.domain_dropdown.attach_to:
                self.domain_dropdown.dismiss()

    def _on_domain_search(self, instance, value):
        self._update_domain_dropdown()
        if self.domain_search_input.focus and not self.domain_dropdown.attach_to:
            self.domain_dropdown.open(self.domain_search_input)

    def _on_domain_dropdown_select(self, instance, label=None):
        # label: a kiválasztott domain (label)
        if label is None:
            label = instance.text
        self.domain_search_input.text = label
        self.domain_dropdown.dismiss()
        # Kiválasztott domain alapján zóna beállítása
        for z in self.zones:
            l = f"{z['name']} ({z.get('account_label',z['account_id'])})"
            if l == label:
                self.selected_zone_id = z["id"]
                self.selected_account = z["account_id"]
                self.selected_token = self.account_zone_map[z["id"]][1]
                break
        self.load_records()

    def _on_record_search(self, instance, value):
        self.refresh_records_grid()

    def load_records(self):
        self.show_loading()
        Clock.schedule_once(lambda dt: self._do_load_records(), 0.1)

    def _do_load_records(self):
        self.records = get_dns_records(self.selected_token, self.selected_zone_id)
        self.refresh_records_grid()
        self.hide_loading()

    def show_toast(self, message, success=True):
        from kivy.uix.label import Label
        from kivy.uix.modalview import ModalView
        toast = ModalView(size_hint=(None, None), size=(220, 48), background_color=(0,0,0,0), auto_dismiss=True)
        color = (0.2, 0.8, 0.2, 1) if success else (1, 0.3, 0.3, 1)
        label = Label(text=message, font_size=16, color=color, size_hint=(1, 1), halign='center', valign='middle')
        toast.add_widget(label)
        toast.open()
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: toast.dismiss(), 2)

    def show_token_tutorial(self, *args):
        tutorial_text = (
            "How to create a Cloudflare API Token for this app:\n\n"
            "1. Log in to your Cloudflare dashboard.\n"
            "2. Go to 'Manage Account' > 'Account API Tokens'.\n"
            "3. Click the 'Create Token' button.\n"
            "4. At the bottom, select 'Create Custom Token'.\n"
            "5. Token name: Any name, e.g. 'Cloudflare DNS Manager GUI'.\n"
            "6. Permissions: Add two permissions:\n"
            "   - Zone - DNS - Edit\n"
            "   - Zone - Cache Purge - Purge\n"
            "7. Zone Resources: Include - All zones from your account.\n"
            "8. Click 'Continue to Summary', then 'Create Token'.\n"
            "9. Copy the generated Token.\n"
            "10. On the token page, you will also see a 'test this token' section.\n"
            "    The URL will look like: https://api.cloudflare.com/client/v4/accounts/123asd123asd123asd123asd123asd123/tokens/verify\n"
            "    The part after /accounts/ is your Account ID.\n"
            "\nPaste the Token and Account ID into the app.\n"
        )
        popup = Popup(title="Create Token Tutorial", size_hint=(None, None), size=(580, 560), auto_dismiss=True)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=12)
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        label = Label(text=tutorial_text, color=CLOUDFLARE_LIGHT, font_size=15, halign='left', valign='top', text_size=(480, None))
        label.bind(texture_size=lambda instance, value: setattr(label, 'height', value[1]))
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(label)
        layout.add_widget(scroll)
        close_btn = Button(text="Close", size_hint=(1, None), height=40, background_color=(.7,.7,.7,1), font_size=15)
        close_btn.bind(on_release=lambda i: popup.dismiss())
        layout.add_widget(close_btn)
        popup.content = layout
        popup.open()

    def check_for_update(self):
        from kivy.clock import Clock
        def do_check():
            import requests
            try:
                resp = requests.get(UPDATE_INFO_URL, timeout=5)
                if resp.ok:
                    data = resp.json()
                    latest_version = data.get("version", "0.0.0")
                    download_url = data.get("download_url", "")
                    if self._is_newer_version(latest_version, APP_VERSION):
                        Clock.schedule_once(lambda dt: self._show_update_popup(latest_version, download_url))
                    else:
                        Clock.schedule_once(lambda dt: self._show_update_popup(latest_version, None, up_to_date=True))
                else:
                    Clock.schedule_once(lambda dt: self._show_update_popup(None, None, failed=True, fail_reason=f"HTTP error: {resp.status_code}"))
            except Exception as exc:
                fail_reason = str(exc)
                Clock.schedule_once(lambda dt: self._show_update_popup(None, None, failed=True, fail_reason=fail_reason))
        threading.Thread(target=do_check, daemon=True).start()

    def _is_newer_version(self, latest, current):
        def parse(v):
            return [int(x) for x in v.split(".")]
        return parse(latest) > parse(current)

    def _show_update_popup(self, latest_version, download_url, up_to_date=False, failed=False, fail_reason=None):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        layout = BoxLayout(orientation='vertical', padding=20, spacing=16)
        if failed:
            msg = "Update check failed!"
            if fail_reason:
                msg += f"\nReason: {fail_reason}"
            layout.add_widget(Label(text=msg, font_size=16, color=(1,0.3,0.3,1)))
        elif up_to_date:
            layout.add_widget(Label(text="You have the latest version.", font_size=17, color=(0.2,0.8,0.2,1)))
        elif latest_version and download_url:
            layout.add_widget(Label(text=f"New version available: {latest_version}", font_size=17, color=(0.2,0.6,1,1)))
            layout.add_widget(Label(text=f"Current version: {APP_VERSION}", font_size=15, color=CLOUDFLARE_LIGHT))
        else:
            layout.add_widget(Label(text="Unknown update status.", font_size=17, color=(1,0.3,0.3,1)))
        btn_row = BoxLayout(orientation='horizontal', spacing=12, size_hint=(1, None), height=44)
        if not failed and latest_version and download_url:
            download_btn = Button(text="Download update", size_hint=(1, 1), background_color=(0.2,0.6,1,1), color=CLOUDFLARE_WHITE, font_size=16)
            def on_download(inst):
                webbrowser.open(download_url)
            download_btn.bind(on_release=on_download)
            btn_row.add_widget(download_btn)
        close_btn = Button(text="Close", size_hint=(1, 1), background_color=(.7,.7,.7,1), font_size=16)
        close_btn.bind(on_release=lambda i: popup.dismiss())
        btn_row.add_widget(close_btn)
        layout.add_widget(btn_row)
        popup = Popup(title="Update", size_hint=(None, None), size=(420, 220), auto_dismiss=True)
        popup.content = layout
        popup.open()

    def show_about_popup(self, *args):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        layout = BoxLayout(orientation='vertical', padding=20, spacing=16)
        info = (
            f"Cloudflare DNS Manager GUI\n"
            f"Version: {APP_VERSION}\n"
            f"Author: Gergo Sofalvi\n"
            f"Website: cfdnsmanager.geri.app\n\n"
            f"This application uses the Cloudflare Account API.\n"
            f"The user interface is built with Python and Kivy.\n\n"
            f"You can manage multiple Cloudflare accounts, domains, and DNS records easily.\n"
            f"All data is stored locally."
        )
        layout.add_widget(Label(text=info, font_size=15, color=CLOUDFLARE_LIGHT, halign='left', valign='top', text_size=(380, None)))
        close_btn = Button(text="Close", size_hint=(1, None), height=40, background_color=(.7,.7,.7,1), font_size=15)
        close_btn.bind(on_release=lambda i: popup.dismiss())
        layout.add_widget(close_btn)
        popup = Popup(title="About", size_hint=(None, None), size=(420, 320), auto_dismiss=True)
        popup.content = layout
        popup.open()

class CloudflareDNSApp(App):
    icon = resource_path('Cloudflare32px.icns')  # Dock és tálca ikon beállítása
    def build(self):
        from kivy.core.window import Window  # Import Window at the start of build
        # ESC gomb letiltása főablakra
        Window.bind(on_keyboard=self._on_keyboard)
        # Ablak méret/pozíció visszaállítása
        win_settings = load_window_settings()
        if win_settings:
            Window.size = tuple(win_settings.get("size", Window.size))
            Window.left, Window.top = win_settings.get("pos", (Window.left, Window.top))
        # Ikon beállítása futás közben is (ha a .icns nem működne, próbáljuk png-vel is)
        try:
            Window.set_icon(resource_path('Cloudflare32px.icns'))
        except Exception:
            try:
                Window.set_icon(resource_path('Cloudflare32px.png'))
            except Exception:
                pass
        # Mentés események
        Window.bind(on_resize=self._on_window_resize)
        Window.bind(on_move=self._on_window_move)
        manager = DNSManager()
        manager.check_for_update()  # Indításkor ellenőrizze a frissítést
        return manager

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        # 27 az ESC gomb
        if key == 27:
            # Ha van nyitott popup, azt zárja be, de ne lépjen ki az appból
            for w in EventLoop.window.children[:]:
                if hasattr(w, 'dismiss') and getattr(w, 'auto_dismiss', False):
                    w.dismiss()
                    return True  # Ne lépjen ki
            return True  # Ne lépjen ki
        return False

    def _on_window_resize(self, instance, width, height):
        from kivy.core.window import Window
        save_window_settings([Window.width, Window.height], [Window.left, Window.top])

    def _on_window_move(self, instance, *args):
        from kivy.core.window import Window
        # args: lehet (pos,) vagy (x, y), vagy üres
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            pos = list(args[0])
        elif len(args) == 2:
            pos = [args[0], args[1]]
        else:
            pos = [Window.left, Window.top]
        save_window_settings([Window.width, Window.height], pos)

if __name__ == "__main__":
    CloudflareDNSApp().run() 