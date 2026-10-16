import os
import subprocess
import sys
import hashlib
import threading

try:
    import gi   
    gi.require_version('Gtk', '4.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
except Exception as e:
    print(f"Missing dependencies: {e}")
    sys.exit(1)

WALLPAPER_DIR = os.path.expanduser("~/Pictures/CyberWalls")
SUPPORTED = ('.jpg', '.jpeg', '.png')
THUMB_WIDTH = 260
THUMB_HEIGHT = 150
CACHE_DIR = os.path.expanduser("~/.cache/wallpaper-picker")
os.makedirs(CACHE_DIR, exist_ok=True)

def load_thumbnail(path: str) -> GdkPixbuf.Pixbuf | None:
    try:
        mtime = str(os.path.getmtime(path))
        key = hashlib.md5((path + mtime).encode()).hexdigest()
        cache_path = os.path.join(CACHE_DIR, key + ".png")

        if os.path.exists(cache_path):
            return GdkPixbuf.Pixbuf.new_from_file(cache_path)
        
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
        self.set_default_size(1200, 220)

        self.swaybg_proc = None
        self.loading = False
        self.loaded = False

        self._build_ui()
        self._apply_css()

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect('key-pressed', self._on_key)
        self.add_controller(key_ctrl)

        self.connect('close-request', self._on_close_request)

    def _build_ui(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)

        self.flow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.flow.set_valign(Gtk.Align.FILL)
        scroll.set_child(self.flow)
        
        self.set_child(scroll)

    def show_picker(self):
        self.present()
        
        if not self.loaded and not self.loading:
            self.loading = True
            threading.Thread(target=self._load_wallpapers_async, daemon=True).start()

    def _load_wallpapers_async(self):
        try:
            if not os.path.isdir(WALLPAPER_DIR):
                os.makedirs(WALLPAPER_DIR, exist_ok=True)

            files = sorted([
                f for f in os.listdir(WALLPAPER_DIR)
                if f.lower().endswith(SUPPORTED)
            ])

            for fname in files:
                path = os.path.join(WALLPAPER_DIR, fname)
                pixbuf = load_thumbnail(path)
                if pixbuf:
                    GLib.idle_add(self._add_thumb, path, fname, pixbuf)
            
            GLib.idle_add(self._mark_loaded, True)
        except Exception as e:
            print(f"Failed to load wallpapers: {e}", file=sys.stderr)
            GLib.idle_add(self._mark_loaded, False)

    def _mark_loaded(self, success: bool):
        self.loading = False
        if success:
            self.loaded = True
        return False

    def _add_thumb(self, path, fname, pixbuf):
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

    def set_wallpaper(self, path: str):
        if self.swaybg_proc and self.swaybg_proc.poll() is None:
            self.swaybg_proc.terminate()
            try:
                self.swaybg_proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.swaybg_proc.kill()
        
        self.swaybg_proc = subprocess.Popen(['swaybg', '-i', path, '-m', 'fill'])

    def _apply(self, path):
        self.set_wallpaper(path)
        self.set_visible(False)

    def _on_close_request(self, *args):
        self.set_visible(False)
        return True

    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.set_visible(False)
            return True
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
            border: 1px solid #ff0055;
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
        super().__init__(
            application_id='dev.deepstar.wallpaper-picker',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = WallpaperPicker(self)
        self.win.show_picker()


if __name__ == '__main__':
    app = WallpaperApp()
    app.run(sys.argv)