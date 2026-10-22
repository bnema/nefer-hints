"""Deterministic synthetic GTK scenes; launch with the system Python."""
import argparse
import json
import math
import random
import traceback
from pathlib import Path

TEMPLATES = ('files-grid', 'files-list', 'settings', 'preferences-dialog',
             'table', 'editor', 'context-menu', 'app-menu', 'sidebar-nav', 'form')


def intersect(a, b):
    return max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])


def visible_fraction(original, clipped):
    area = max(0, original[2]-original[0]) * max(0, original[3]-original[1])
    return (max(0, clipped[2]-clipped[0]) * max(0, clipped[3]-clipped[1]) / area) if area else 0


def centre_under(box, popup):
    x, y = (box[0]+box[2])/2, (box[1]+box[3])/2
    return popup[0] <= x < popup[2] and popup[1] <= y < popup[3]


def clip_box(box, clips):
    clipped = box
    for rect in clips:
        clipped = intersect(clipped, rect)
    if (visible_fraction(box, clipped) < .5 or
            clipped[2]-clipped[0] < 4 or clipped[3]-clipped[1] < 4):
        return None
    result = [math.floor(clipped[0]), math.floor(clipped[1]),
              math.ceil(clipped[2]), math.ceil(clipped[3])]
    return result if result[2]-result[0] >= 4 and result[3]-result[1] >= 4 else None


def main():
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, Gdk, GLib, Gio

    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--template', choices=TEMPLATES, required=True)
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--accent', default='#3584e4')
    parser.add_argument('--font-scale', type=float, default=1.)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'ready').unlink(missing_ok=True)
    import re
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', args.accent) or not .9 <= args.font_scale <= 1.25:
        parser.error('invalid accent or font scale')
    rng = random.Random(args.seed)
    app = Adw.Application(application_id='org.example.FictionalStudio', flags=Gio.ApplicationFlags.NON_UNIQUE)
    targets, scrolls = [], []
    popup = None

    def mark(widget, kind='other', disable=True):
        targets.append((widget, kind))
        if disable and rng.random() < .12:
            widget.set_sensitive(False)
        return widget

    def button(label, kind='other'):
        return mark(Gtk.Button(label=label), kind)

    def box(vertical=True, spacing=10):
        return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)

    def padded(widget, margin=18):
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(widget, 'set_margin_'+side)(margin)
        return widget

    def entry(text='Search fictional archive'):
        w = Gtk.Entry(placeholder_text=text)
        w.set_hexpand(True)
        return mark(w, 'field')

    def scroll(child):
        w = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        w.set_child(child)
        scrolls.append(w)
        return w

    def settings():
        content = padded(box())
        for i in range(rng.randint(2, 4)):
            row = box(False)
            row.append(Gtk.Label(label=f'{rng.choice(["Lumen", "Velora", "Aster"])} option {i}', hexpand=True, xalign=0))
            row.append(mark(Gtk.Switch(valign=Gtk.Align.CENTER)))
            content.append(row)
        for label in ('Enable starlight', 'Keep fictional drafts'):
            content.append(mark(Gtk.CheckButton(label=label)))
        first = None
        for label in ('Quiet mode', 'Bright mode', 'Automatic mode'):
            w = Gtk.CheckButton(label=label)
            if first:
                w.set_group(first)
            else:
                first = w
            content.append(mark(w))
        content.append(mark(Gtk.SpinButton.new_with_range(1, 99, 1), 'field'))
        content.append(mark(Gtk.DropDown.new_from_strings(['Aurora', 'Nebula', 'Comet']), 'field'))
        content.append(mark(Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)))
        exp = Gtk.Expander(label='Advanced fictional options')
        exp.set_child(Gtk.Label(label='Synthetic configuration details'))
        # Only the expander header is interactive, not its expanded child.
        content.append(exp)
        mark(exp.get_first_child(), disable=False)
        return content

    def activate(application):
        nonlocal popup
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK if args.theme == 'dark' else Adw.ColorScheme.FORCE_LIGHT)
        css = Gtk.CssProvider()
        css.load_from_string(f':root {{ --accent-bg-color: {args.accent}; --accent-color: {args.accent}; }} * {{ font-size: {11*args.font_scale}pt; }}')
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = Adw.ApplicationWindow(application=application, title='Fictional Studio')
        root = box(spacing=0)
        win.set_content(root)
        toolbar = Gtk.HeaderBar() if rng.choice([True, False]) else box(False)
        if isinstance(toolbar, Gtk.HeaderBar):
            toolbar.set_show_title_buttons(False)
        root.append(toolbar)
        def tool(w):
            if isinstance(toolbar, Gtk.HeaderBar):
                toolbar.pack_start(w)
            else:
                toolbar.append(w)
        for icon, label in [('go-previous-symbolic', 'Back'), ('folder-new-symbolic', 'New folder'), ('view-refresh-symbolic', 'Refresh')]:
            tool(mark(Gtk.Button(icon_name=icon) if rng.choice([True, False]) else Gtk.Button(label=label), 'icon_button'))
        tool(entry())
        menu = mark(Gtk.MenuButton(icon_name='open-menu-symbolic'), 'icon_button', disable=False)
        tool(menu)
        pop = Gtk.Popover(autohide=False)
        popcontent = padded(box(spacing=4), 8)
        for label in ('Open constellation', 'Copy fictional item', 'Rename', 'Archive', 'Properties'):
            popcontent.append(button(label, 'menu_item'))
        pop.set_child(popcontent)
        menu.set_popover(pop)
        body = box(False)
        root.append(body)
        body.set_vexpand(True)
        template = args.template
        if template in ('files-grid', 'files-list', 'context-menu', 'sidebar-nav', 'app-menu'):
            sidebar = padded(box(), 12)
            sidebar.set_size_request(200, -1)
            for label in ('Home', 'Constellations', 'Sketches', 'Clouds', 'Archive'):
                sidebar.append(button(label, 'row_file'))
            body.append(sidebar)
        content = padded(box())
        content.set_hexpand(True)
        body.append(content)
        if template in ('files-grid', 'files-list', 'context-menu', 'app-menu'):
            path = box(False)
            for label in ('Fictional', 'Lumen', 'Documents'):
                path.append(button(label))
            content.append(path)
            files = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE) if template == 'files-grid' else box(spacing=4)
            if isinstance(files, Gtk.FlowBox):
                files.set_max_children_per_line(7)
                files.set_min_children_per_line(4)
                files.set_valign(Gtk.Align.START)
            for i in range(rng.randint(45, 65)):
                name = f'{rng.choice(["Lumen", "Velora", "Nacre", "Orbin"])}-{i:02d}.draft'
                w = button(('◇\n' if template == 'files-grid' else '◇   ') + name, 'row_file')
                w.set_size_request(145 if template == 'files-grid' else -1, 92 if template == 'files-grid' else rng.choice([34, 42]))
                files.append(w)
            content.append(scroll(files))
        elif template == 'settings':
            content.append(scroll(settings()))
        elif template == 'preferences-dialog':
            content.append(button('Open preferences'))
            # Adw.Dialog lives in the parent's widget tree: no guessed Wayland
            # toplevel position or CSD offset is needed for modal coordinates.
            targets.clear()
            dialog = Adw.Dialog(title='Fictional preferences', content_width=650, content_height=740)
            pane = box()
            pane.append(Gtk.Label(label='Fictional preferences'))
            pane.append(settings())
            pane.append(button('Close'))
            dialog.set_child(padded(pane))
            # Modal parent is not interactive; targets were cleared above.
            self_windows.append(dialog)
        elif template == 'form':
            for label in ('Project title', 'Fictional address', 'Access phrase', *(['Constellation code'] if rng.choice([True, False]) else [])):
                content.append(Gtk.Label(label=label, xalign=0))
                content.append(mark(Gtk.PasswordEntry() if label == 'Access phrase' else Gtk.Entry(), 'field'))
            text = Gtk.TextView(vexpand=True)
            text.get_buffer().set_text('Fictional project description. Text body is not a target.')
            content.append(scroll(text))
            content.append(mark(Gtk.DropDown.new_from_strings(['Lumen', 'Nacre', 'Velora']), 'field'))
            content.append(mark(Gtk.CheckButton(label='Accept fictional terms')))
            radio = Gtk.CheckButton(label='Private')
            content.append(mark(radio))
            other = Gtk.CheckButton(label='Shared', group=radio)
            content.append(mark(other))
            for label in ('Submit', 'Cancel'):
                content.append(button(label))
        elif template == 'editor':
            tabs = box(False)
            for i in range(rng.randint(2, 5)):
                tabs.append(button(f'Starlight {i}.txt', 'tab'))
            content.append(tabs)
            text = Gtk.TextView(vexpand=True)
            text.get_buffer().set_text(('A fictional journey through the Lumen gardens.\n\n' * 30))
            content.append(scroll(text))
        elif template == 'sidebar-nav':
            tabs = box(False)
            for label in ('Overview', 'Activity', 'Collections'):
                tabs.append(button(label, 'tab'))
            content.append(tabs)
            for i in range(rng.randint(4, 8)):
                content.append(mark(Gtk.LinkButton(uri=f'https://example.invalid/fiction/{i}', label=f'Explore fictional constellation {i}'), 'text_link'))
            content.append(button('Create collection'))
        elif template == 'table':
            model = Gtk.StringList.new([f'{rng.choice(["Lumen", "Nacre", "Velora"])} {i:03d}' for i in range(rng.randint(65, 90))])
            sorted_model = Gtk.SortListModel(model=model)
            view = Gtk.ColumnView(model=Gtk.SingleSelection(model=sorted_model), vexpand=True)
            sorted_model.set_sorter(view.get_sorter())
            for index, title in enumerate(('Name', 'Category', 'Status', 'Revision')):
                factory = Gtk.SignalListItemFactory()
                def setup(factory, item, index=index):
                    w = Gtk.Label(xalign=0, margin_top=9, margin_bottom=9)
                    item.set_child(w)
                def bind(factory, item, index=index):
                    item.get_child().set_label(item.get_item().get_string() if index == 0 else ('Draft', 'Ready', '4')[index-1])
                factory.connect('setup', setup)
                factory.connect('bind', bind)
                column = Gtk.ColumnViewColumn(title=title, factory=factory, expand=True)
                column.set_sorter(Gtk.StringSorter(expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, 'string')))
                view.append_column(column)
            content.append(scroll(view))
        win.fullscreen()
        win.present()
        for dialog in self_windows:
            dialog.present(win)
        def settle():
            nonlocal popup
            for sw in scrolls:
                adj = sw.get_vadjustment()
                adj.set_value(rng.random() * max(0, adj.get_upper()-adj.get_page_size()) * .6)
            if template in ('context-menu', 'app-menu'):
                popup = pop
                if template == 'context-menu':
                    from gi.repository import Gdk as GD
                    rect = GD.Rectangle()
                    rect.x, rect.y, rect.width, rect.height = rng.randint(200, 700), rng.randint(150, 400), 1, 1
                    pop.unparent()
                    pop.set_parent(content)
                    pop.set_pointing_to(rect)
                pop.popup()
                if template == 'app-menu':
                    menu.popup()
            GLib.timeout_add(1300, export)
            return False
        frames = [0]
        def after_frames(widget, clock):
            frames[0] += 1
            if frames[0] < 4:
                return True
            GLib.timeout_add(600, settle)
            return False
        win.add_tick_callback(after_frames)

    self_windows = []

    def bounds(widget, ancestor):
        ok, rect = widget.compute_bounds(ancestor)
        if not ok:
            raise RuntimeError('cannot compute widget bounds')
        return (rect.get_x(), rect.get_y(), rect.get_x()+rect.get_width(), rect.get_y()+rect.get_height())

    def export():
        try:
            win = next(w for w in app.get_windows() if isinstance(w, Gtk.ApplicationWindow))
            width, height = win.get_width(), win.get_height()
            # Discover internal interactive widgets (dropdown arrows, scrollbars,
            # table headers/rows) without double-labelling registered composites.
            registered = {w for w, k in targets}
            def walk(w):
                if w in registered:
                    return
                name = w.get_css_name()
                kind = None
                if w.__gtype__.name == 'GtkColumnViewTitle':
                    kind = 'other'
                elif name == 'row' and args.template == 'table':
                    kind = 'row_file'
                elif isinstance(w, (Gtk.Button, Gtk.Range)):
                    kind = 'icon_button' if isinstance(w, Gtk.Button) else 'other'
                if kind:
                    targets.append((w, kind))
                    return
                child = w.get_first_child()
                while child:
                    walk(child)
                    child = child.get_next_sibling()
            for root in self_windows or [win]:
                walk(root)
            popup_rect = None
            if popup:
                if not popup.get_mapped():
                    raise RuntimeError('requested popup is not mapped')
                surface = popup.get_native().get_surface()
                px, py = surface.get_position_x(), surface.get_position_y()
                popup_rect = (px, py, px+surface.get_width(), py+surface.get_height())
            result = []
            for widget, kind in targets:
                if not widget.get_visible() or not widget.get_mapped() or not widget.get_sensitive() or not widget.is_sensitive():
                    continue
                native = widget.get_native()
                if native is None:
                    continue
                surface = native.get_surface()
                if isinstance(surface, Gdk.Popup):
                    rect = bounds(widget, native)
                    dx, dy = surface.get_position_x(), surface.get_position_y()
                else:
                    rect = bounds(widget, widget.get_root())
                    dx = dy = 0
                rect = (rect[0]+dx, rect[1]+dy, rect[2]+dx, rect[3]+dy)
                clips = [(0, 0, width, height)]
                parent = widget.get_parent()
                while parent:
                    if isinstance(parent, (Gtk.ScrolledWindow, Gtk.Viewport)) or parent.get_css_name() == 'listview':
                        c = bounds(parent, native if isinstance(surface, Gdk.Popup) else widget.get_root())
                        clips.append((c[0]+dx, c[1]+dy, c[2]+dx, c[3]+dy))
                    parent = parent.get_parent()
                clipped = clip_box(rect, clips)
                if clipped and not (popup_rect and not isinstance(surface, Gdk.Popup) and centre_under(rect, popup_rect)):
                    result.append(clipped+[kind])
            data = dict(toolkit='gtk', template=args.template, seed=args.seed, theme=args.theme, accent=args.accent, font_scale=args.font_scale, width=width, height=height, boxes=result)
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out/'labels.json').write_text(json.dumps(data, indent=2))
            (args.out/'ready').touch()
        except Exception:
            traceback.print_exc()
            app.quit()
            failures.append(True)
        return False

    failures = []
    import sys
    def callback_error(exc_type, value, tb):
        traceback.print_exception(exc_type, value, tb)
        (args.out/'ready').unlink(missing_ok=True)
        failures.append(True)
        app.quit()
    sys.excepthook = callback_error
    app.connect('activate', activate)
    code = app.run([])
    raise SystemExit(1 if failures else code)


if __name__ == '__main__':
    main()
