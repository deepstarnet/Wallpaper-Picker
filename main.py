#!/usr/bin/env python3

import os
import subprocess
import sys
import hashlib

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
except Exception as e:
    print(f"Missing dependencies: {e}")
    print("Run: sudo dnf install python3-gobject gtk4 gdk-pixbuf2")
    sys.exit(1)

WALLPAPER_DIR = os.path.expanduser("~/Wallpapers")
SUPPORTED = ('.jpg', '.jpeg', '.png')
THUMB_SIZE = 220
WINDOW_HEIGHT = 300
CASHE_DIR = os.path.expanduser("~/.cache/wallpaper-picker")
os.makedirs(CASHE_DIR, exist_ok=True)

def set_wallpaper(path: str):
    uri = f"file://{path}"
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background',
                    'picture-uri', uri], check=False)
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background',
                    'picture-uri-dark', uri], check=False)


def load_thumbnail(path: str) -> GdkPixbuf.Pixbuf | None:
    mtime = str(os.path.getmtime(path))
    key = hashlib.md5((path + mtime).encode()).hexdigest()
    cache_path = os.path.join(CASHE_DIR, key + ".png")

    if os.path.exists(cache_path):
        return GdkPixbuf.Pixbuf.new_from_file(cache_path)
    
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, THUMB_SIZE, THUMB_SIZE, True)
        pixbuf.savev(cache_path, "png", [], [])
        return pixbuf
    except Exception:
        return

class WallpaperPicker(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)

        self.set_decorated(False)
        self.set_resizable(False)

        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        geo = monitor.get_geometry()

        win_width = min(geo.width - 80, 1200)
        self.set_default_size(win_width, WINDOW_HEIGHT)

        # Position: bottom center
        self.set_size_request(win_width, WINDOW_HEIGHT)
        GLib.idle_add(self._position_window, geo, win_width)

        self._build_ui()
        self._load_wallpapers()
        self._apply_css()

        # Close on Escape
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect('key-pressed', self._on_key)
        self.add_controller(key_ctrl)

        # Close on click outside
        click_ctrl = Gtk.GestureClick()
        click_ctrl.connect('pressed', self._on_outside_click)
        self.add_controller(click_ctrl)

    def _position_window(self, geo, win_width):
        x = geo.x + (geo.width - win_width) // 2
        y = geo.y + geo.height - WINDOW_HEIGHT - 10
        self.present()
        return False

    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(outer)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.set_margin_start(16)
        header.set_margin_end(16)
        header.set_margin_top(10)
        header.set_margin_bottom(8)

        label = Gtk.Label(label="WALLPAPERS")
        label.add_css_class('header-label')
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        header.append(label)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class('close-btn')
        close_btn.connect('clicked', lambda _: self.close())
        header.append(close_btn)

        outer.append(header)

        # Separator line
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.add_css_class('neon-sep')
        outer.append(sep)

        # Scroll area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scroll.set_vexpand(True)
        scroll.set_margin_top(10)
        scroll.set_margin_bottom(10)
        scroll.set_margin_start(10)
        scroll.set_margin_end(10)

        self.flow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.flow.set_valign(Gtk.Align.CENTER)
        scroll.set_child(self.flow)
        outer.append(scroll)

    def _load_wallpapers(self):
        if not os.path.isdir(WALLPAPER_DIR):
            os.makedirs(WALLPAPER_DIR, exist_ok=True)

        files = sorted([
            f for f in os.listdir(WALLPAPER_DIR)
            if f.lower().endswith(SUPPORTED)
        ])

        for fname in files:
            path = os.path.join(WALLPAPER_DIR, fname)
            GLib.idle_add(self._add_thumb, path, fname)

    def _add_thumb(self, path, fname):
        pixbuf = load_thumbnail(path)
        if not pixbuf:
            return False

        btn = Gtk.Button()
        btn.add_css_class('thumb-btn')
        btn.set_tooltip_text(fname)

        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        img = Gtk.Picture.new_for_paintable(texture)
        img.set_size_request(THUMB_SIZE, int(THUMB_SIZE * 0.56))
        img.set_content_fit(Gtk.ContentFit.COVER)

        btn.set_child(img)
        btn.connect('clicked', lambda _, p=path: self._apply(p))
        self.flow.append(btn)
        return False

    def _apply(self, path):
        set_wallpaper(path)
        self.close()

    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
        return False

    def _on_outside_click(self, ctrl, n, x, y):
        pass

    def _apply_css(self):
        css = b"""
        window {
            background-color: rgba(10, 10, 15, 0.96);
            border-top: 1px solid rgba(0, 255, 159, 0.4);
            border-radius: 8px 8px 0 0;
        }
        .header-label {
            font-family: monospace;
            font-size: 11px;
            font-weight: bold;
            color: rgba(0, 255, 159, 0.85);
            letter-spacing: 2px;
        }
        .close-btn {
            background: transparent;
            border: none;
            color: rgba(200, 200, 204, 0.5);
            font-size: 12px;
            padding: 2px 6px;
            min-width: 0;
            min-height: 0;
        }
        .close-btn:hover {
            color: #ff3c5a;
        }
        .neon-sep {
            background-color: rgba(0, 255, 159, 0.2);
            min-height: 1px;
        }
        .thumb-btn {
            background: rgba(30, 44, 66, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 6px;
            padding: 3px;
            transition: border-color 150ms;
        }
        .thumb-btn:hover {
            border-color: rgba(0, 255, 159, 0.7);
            background: rgba(0, 255, 159, 0.05);
        }
        scrollbar {
            background: transparent;
        }
        scrollbar slider {
            background-color: rgba(0, 255, 159, 0.25);
            border-radius: 4px;
            min-height: 4px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


class WallpaperApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='dev.deepstar.wallpaper-picker')

    def do_activate(self):
        win = WallpaperPicker(self)
        win.present()


if __name__ == '__main__':
    app = WallpaperApp()
    app.run(sys.argv)