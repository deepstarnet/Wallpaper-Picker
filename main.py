import os
import subprocess
import sys
import hashlib

try:
    import gi   
    gi.require_version('Gtk', '4.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
except Exception as e:
    print(f"Missing dependencies: {e}")
    print("Run: sudo dnf install python3-gobject gtk4 gdk-pixbuf2")
    sys.exit(1)

WALLPAPER_DIR = os.path.expanduser("~/Pictures/CyberWalls")
SUPPORTED = ('.jpg', '.jpeg', '.png')
THUMB_WIDTH = 260
THUMB_HEIGHT = 150
CACHE_DIR = os.path.expanduser("~/.cache/wallpaper-picker")
os.makedirs(CACHE_DIR, exist_ok=True)

def set_wallpaper(path: str):
    subprocess.run(['pkill', 'swaybg'], check=False)
    subprocess.Popen(['swaybg', '-i', path, '-m', 'fill'])

def load_thumbnail(path: str) -> GdkPixbuf.Pixbuf | None:
    mtime = str(os.path.getmtime(path))
    key = hashlib.md5((path + mtime).encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, key + ".png")

    if os.path.exists(cache_path):
        return GdkPixbuf.Pixbuf.new_from_file(cache_path)
    
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, THUMB_WIDTH, THUMB_HEIGHT, False)
        pixbuf.savev(cache_path, "png", [], [])
        return pixbuf
    except Exception:
        return None

class WallpaperPicker(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)

        self.set_decorated(False)
        self.set_resizable(False)

        # Выставляем размер под горизонт-ленту
        self.set_default_size(1200, 220)

        self._build_ui()
        self._load_wallpapers()
        self._apply_css()

        # Закрытие по Escape
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect('key-pressed', self._on_key)
        self.add_controller(key_ctrl)

    def _build_ui(self):
        # Горизонтальный скролл без шапки и рамок, как в Rofi
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)

        # Плотный горизонтальный поток без спайсинга (margin/padding: 0)
        self.flow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.flow.set_valign(Gtk.Align.FILL)
        scroll.set_child(self.flow)
        
        self.set_child(scroll)

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
        btn.add_css_class('element')
        btn.set_tooltip_text(fname)

        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        img = Gtk.Picture.new_for_paintable(texture)
        img.add_css_class('element-icon')
        img.set_size_request(THUMB_WIDTH, THUMB_HEIGHT)
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

    def _apply_css(self):
        css = """
        window {
            background-color: #0f1015;
            border: 1px solid #1e2029;
            border-radius: 0px;
        }

        .element {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 0px;
            padding: 0px;
            margin: 0px;
            box-shadow: none;
        }

        .element:hover, .element:focus {
            border: 1px solid #ff0055; /* аналог @re0 из rofi */
            background: transparent;
        }

        .element-icon {
            margin: 0px;
            padding: 0px;
            border-radius: 0px;
        }

        scrollbar, scrollbar slider {
            min-width: 0px;
            min-height: 0px;
            opacity: 0;
            background: transparent;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
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