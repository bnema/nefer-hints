"""Deterministic fictional Qt targets. Run with the system PySide6 interpreter."""
import argparse
import json
import random
import sys
from pathlib import Path

TEMPLATES = ('files-grid', 'files-list', 'settings', 'preferences-dialog', 'table',
             'editor', 'context-menu', 'app-menu', 'sidebar-nav', 'form')


def clip_box(box, bounds, minimum_fraction=0.5):
    """Intersect exclusive-end rectangles, rejecting mostly hidden/small targets."""
    x, y, r, b = box
    a, c, d, e = bounds
    clipped = (max(x, a), max(y, c), min(r, d), min(b, e))
    w, h = clipped[2] - clipped[0], clipped[3] - clipped[1]
    if w < 4 or h < 4 or w * h < (r - x) * (b - y) * minimum_fraction:
        return None
    return list(clipped)


def covered(box, surface):
    x, y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return surface[0] <= x < surface[2] and surface[1] <= y < surface[3]


def main():
    from PySide6 import QtCore as C, QtGui as G, QtWidgets as W
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--template', choices=TEMPLATES, required=True)
    parser.add_argument('--theme', choices=('light', 'dark'), required=True)
    parser.add_argument('--accent', default='#4488dd')
    parser.add_argument('--font-scale', type=float, default=1.0)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'ready').unlink(missing_ok=True)
    rng = random.Random(args.seed)
    app = W.QApplication(sys.argv[:1])

    def fail(exc_type, value, traceback):
        sys.__excepthook__(exc_type, value, traceback)
        app.exit(1)

    sys.excepthook = fail
    app.setStyle('Fusion')
    palette = app.palette()
    dark = args.theme == 'dark'
    for role, light, dim in [('Window', '#f0f0f0', '#303238'), ('WindowText', '#202124', '#eeeeee'),
                              ('Base', '#ffffff', '#202228'), ('AlternateBase', '#edf0f4', '#383a40'),
                              ('Text', '#202124', '#eeeeee'), ('Button', '#e8e9ed', '#40434a'),
                              ('ButtonText', '#202124', '#eeeeee')]:
        palette.setColor(getattr(G.QPalette.ColorRole, role), G.QColor(dim if dark else light))
    for role in (G.QPalette.Highlight, G.QPalette.Accent):
        palette.setColor(role, G.QColor(args.accent))
    palette.setColor(G.QPalette.HighlightedText, G.QColor('white'))
    palette.setColor(G.QPalette.Disabled, G.QPalette.Text, G.QColor('#888888'))
    palette.setColor(G.QPalette.Disabled, G.QPalette.ButtonText, G.QColor('#888888'))
    app.setPalette(palette)
    font = app.font()
    font.setPointSizeF(11 * args.font_scale)
    app.setFont(font)
    window = W.QMainWindow()
    window.setWindowTitle('Aster workspace')
    root = W.QWidget()
    window.setCentralWidget(root)
    layout = W.QVBoxLayout(root)
    layout.setSpacing(rng.choice([6, 10, 14]))
    targets, views, tabs, headers = [], [], [], []
    popup = None
    dialog = None

    def target(widget, kind='other'):
        targets.append((widget, kind))
        return widget

    def button(text, parent_layout):
        b = target(W.QPushButton(text), 'icon_button')
        parent_layout.addWidget(b)
        return b

    def field(parent_layout, text=''):
        w = target(W.QLineEdit(text), 'field')
        parent_layout.addWidget(w)
        return w

    def toolbar(parent_layout):
        row = W.QHBoxLayout()
        parent_layout.addLayout(row)
        for label in rng.sample(['Back', 'Forward', 'Refresh', 'New folder', 'Options'], 4):
            b = button(label if rng.random() > .35 else '◇', row)
            b.setEnabled(rng.random() > .15)
        field(row, '/Aster/Sketches')
        field(row).setPlaceholderText('Search fictional files')

    def list_view(parent_layout, names, grid=False):
        view = W.QListWidget()
        view.setSpacing(4)
        if grid:
            view.setViewMode(W.QListView.IconMode)
            view.setGridSize(C.QSize(150, 100))
            view.setIconSize(C.QSize(40, 40))
            view.setResizeMode(W.QListView.Adjust)
        for i, name in enumerate(names):
            item = W.QListWidgetItem(app.style().standardIcon(W.QStyle.SP_FileIcon), name)
            if i % 9 == args.seed % 9:
                item.setFlags(item.flags() & ~C.Qt.ItemIsEnabled)
            view.addItem(item)
        parent_layout.addWidget(view)
        views.append(view)
        return view

    def preferences(parent_layout):
        switch = target(W.QCheckBox('Enable starlight sync'))
        switch.setChecked(bool(rng.randrange(2)))
        switch.setStyleSheet(
            'QCheckBox::indicator { width: 32px; height: 16px; border-radius: 8px;'
            ' border: 1px solid #888; background: #888; }'
            f'QCheckBox::indicator:checked {{ background: {args.accent}; }}')
        parent_layout.addWidget(switch)
        for i, name in enumerate(rng.sample(['Cloud mist', 'Quiet hours', 'Auto archive', 'Show badges'], rng.randint(3, 4))):
            w = target(W.QCheckBox(name))
            w.setChecked(bool(rng.randrange(2)))
            w.setEnabled(i != args.seed % 4)
            parent_layout.addWidget(w)
        for name in ('Compact', 'Comfortable', 'Spacious'):
            w = target(W.QRadioButton(name))
            parent_layout.addWidget(w)
        spin = target(W.QSpinBox(), 'field')
        spin.setRange(1, 100)
        spin.setValue(rng.randrange(1, 100))
        parent_layout.addWidget(spin)
        combo = target(W.QComboBox(), 'field')
        combo.addItems(['Aster', 'Luma', 'Velora'])
        parent_layout.addWidget(combo)
        slider = target(W.QSlider(C.Qt.Horizontal))
        slider.setValue(rng.randrange(100))
        parent_layout.addWidget(slider)
        expand = target(W.QToolButton())
        expand.setText('Advanced ▸')
        expand.setCheckable(True)
        parent_layout.addWidget(expand)
        details = W.QGroupBox('Archive options')
        inner = W.QVBoxLayout(details)
        button('Reset archive', inner)
        parent_layout.addWidget(details)
        details.hide()
        expand.toggled.connect(details.setVisible)

    t = args.template
    toolbar(layout)
    if t in ('files-grid', 'files-list', 'context-menu', 'app-menu'):
        row = W.QHBoxLayout()
        layout.addLayout(row)
        sidebar = list_view(row, ['Aster home', 'Drafts', 'Sketches', 'Archive', 'Starred'])
        sidebar.setMaximumWidth(220)
        files = list_view(row, [f'{rng.choice(["Luma", "Orin", "Velora", "Mira"])} draft {i:02}.txt'
                                for i in range(rng.randint(65, 95))], t == 'files-grid')
    elif t == 'table':
        table = W.QTableView()
        model = G.QStandardItemModel(75 + rng.randrange(20), 4)
        model.setHorizontalHeaderLabels(['Title', 'Collection', 'Status', 'Size'])
        for i in range(model.rowCount()):
            for j, text in enumerate([f'Aster record {i}', 'Luma', 'Draft', f'{i+3} KB']):
                item = G.QStandardItem(text)
                item.setEnabled(i % 11 != args.seed % 11)
                model.setItem(i, j, item)
        table.setModel(model)
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(W.QAbstractItemView.SelectRows)
        layout.addWidget(table)
        views.append(table)
        headers.append(table.horizontalHeader())
    elif t in ('settings', 'preferences-dialog'):
        preferences(layout)
        layout.addStretch()
        if t == 'preferences-dialog':
            dialog = W.QDialog(window)
            dialog.setWindowTitle('Aster preferences')
            dialog.setModal(True)
            dl = W.QVBoxLayout(dialog)
            preferences(dl)
            button('Apply', dl)
            dialog.resize(620, 620)
    elif t == 'editor':
        bar = W.QTabBar()
        for i in range(rng.randint(3, 6)):
            bar.addTab(f'Fable {i}.txt')
        tabs.append(bar)
        layout.addWidget(bar)
        text = W.QTextEdit('Fictional field notes\n\nThe silver orchard rests beneath an amber sky.\n' * 15)
        layout.addWidget(text)
    elif t == 'sidebar-nav':
        row = W.QHBoxLayout()
        layout.addLayout(row)
        side = list_view(row, ['Overview', 'Collections', 'Activity', 'Archive'])
        side.setMaximumWidth(230)
        content = W.QVBoxLayout()
        row.addLayout(content)
        bar = W.QTabBar()
        for name in ('Summary', 'Recent', 'Shared'):
            bar.addTab(name)
        tabs.append(bar)
        content.addWidget(bar)
        for i in range(rng.randint(3, 7)):
            link = target(W.QLabel(f'<a href="https://example.invalid/{i}">Explore Aster collection {i}</a>'), 'text_link')
            link.setFixedSize(link.sizeHint())
            content.addWidget(link)
        button('Create collection', content)
        content.addStretch()
    elif t == 'form':
        for name in ('Collection title', 'Contact alias', 'Access phrase'):
            layout.addWidget(W.QLabel(name))
            entry = field(layout)
            if name == 'Access phrase':
                entry.setEchoMode(W.QLineEdit.Password)
        layout.addWidget(W.QLabel('Notes (text body is not a target)'))
        layout.addWidget(W.QTextEdit('A fictional collection description.'))
        preferences(layout)
        row = W.QHBoxLayout()
        layout.addLayout(row)
        button('Submit', row)
        button('Cancel', row)

    menu_bar = None
    if t in ('app-menu', 'editor') or rng.random() < .5:
        menu_bar = window.menuBar()
        menu = menu_bar.addMenu('Workspace')
        for name in ('New collection', 'Open draft', 'Save copy', 'Export', 'Close'):
            action = menu.addAction(name)
            action.setEnabled(name != 'Export')
        menu.addSeparator()
        menu.addAction('Preferences')

    window.showFullScreen()

    def settle():
        nonlocal popup
        for view in views:
            view.verticalScrollBar().setValue(rng.randrange(0, max(1, view.verticalScrollBar().maximum() + 1)))
        if dialog:
            dialog.show()
            dialog.move((window.width() - dialog.width()) // 2, (window.height() - dialog.height()) // 2)
        if t == 'context-menu':
            popup = W.QMenu(window)
            for name in ('Open', 'Open in new tab', 'Rename', 'Duplicate', 'Move to archive'):
                action = popup.addAction(name)
                action.setEnabled(name != 'Rename')
            popup.addSeparator()
            popup.addAction('Properties')
            anchor = files.viewport().mapTo(window, C.QPoint(180 + rng.randrange(250), 130 + rng.randrange(200)))
            # A non-grabbing popup needs no input serial in an unattended capture.
            popup.setWindowFlags(C.Qt.ToolTip | C.Qt.FramelessWindowHint)
            popup.popup(window.mapToGlobal(anchor))
        elif t == 'app-menu':
            popup = menu
            popup.setWindowFlags(C.Qt.ToolTip | C.Qt.FramelessWindowHint)
            rect = menu_bar.actionGeometry(menu.menuAction())
            popup.popup(menu_bar.mapToGlobal(rect.bottomLeft() + C.QPoint(0, 1)))
        C.QTimer.singleShot(1300, export)

    def export():
        try:
            if popup and (not popup.isVisible() or not popup.windowHandle().isExposed()):
                raise RuntimeError('Expected menu did not map')
            width, height = window.width(), window.height()
            bounds = (0, 0, width, height)
            boxes = []
            origin = window.mapToGlobal(C.QPoint(0, 0))

            def rect_box(rect, widget):
                if dialog and widget.window() == dialog:
                    # Wayland toplevel global positions are not exposed. The
                    # compositor centres this transient at the requested anchor.
                    p = widget.mapTo(dialog, rect.topLeft()) + C.QPoint(
                        (width - dialog.width()) // 2, (height - dialog.height()) // 2)
                else:
                    p = widget.mapTo(window, rect.topLeft()) if widget.window() == window else widget.mapToGlobal(rect.topLeft()) - origin
                return [p.x(), p.y(), p.x() + rect.width(), p.y() + rect.height()]

            popup_bounds = rect_box(popup.rect(), popup) if popup and popup.isVisible() else None

            def add(box, kind, clip=bounds, top=True):
                result = clip_box(box, clip)
                if result and not (top and popup_bounds and covered(result, popup_bounds)):
                    result = clip_box(result, bounds, 0)
                    if result:
                        boxes.append(result + [kind])

            for scrollbar in window.findChildren(W.QScrollBar):
                if scrollbar.isVisible() and scrollbar.isEnabled() and not dialog:
                    add(rect_box(scrollbar.rect(), scrollbar), 'other')
            for widget, kind in targets:
                if widget.isVisible() and widget.isEnabled() and (not dialog or widget.window() == dialog):
                    add(rect_box(widget.rect(), widget), kind)
            if not dialog:
                for view in views:
                    viewport = view.viewport()
                    clip = rect_box(viewport.rect(), viewport)
                    model = view.model()
                    for row in range(model.rowCount()):
                        index = model.index(row, 0)
                        if not model.flags(index) & C.Qt.ItemIsEnabled:
                            continue
                        rect = view.visualRect(index)
                        if isinstance(view, W.QTableView):
                            rect = rect.united(view.visualRect(model.index(row, model.columnCount() - 1)))
                        add(rect_box(rect, viewport), 'row_file', clip)
                for header in headers:
                    for section in range(header.count()):
                        rect = C.QRect(header.sectionViewportPosition(section), 0, header.sectionSize(section), header.height())
                        add(rect_box(rect, header.viewport()), 'other', rect_box(header.viewport().rect(), header.viewport()))
                for bar in tabs:
                    for i in range(bar.count()):
                        if bar.isTabEnabled(i) and bar.isTabVisible(i):
                            add(rect_box(bar.tabRect(i), bar), 'tab')
                if menu_bar:
                    for action in menu_bar.actions():
                        if action.isEnabled() and action.isVisible():
                            add(rect_box(menu_bar.actionGeometry(action), menu_bar), 'menu_item')
                if popup_bounds:
                    for action in popup.actions():
                        if action.isEnabled() and action.isVisible() and not action.isSeparator():
                            add(rect_box(popup.actionGeometry(action), popup), 'menu_item', top=False)
            data = dict(toolkit='qt', template=t, seed=args.seed, theme=args.theme, accent=args.accent,
                        font_scale=args.font_scale, width=width, height=height, boxes=boxes)
            (args.out / 'labels.json').write_text(json.dumps(data, indent=2))
            (args.out / 'ready').touch()
        except Exception:
            import traceback
            traceback.print_exc()
            app.exit(1)

    C.QTimer.singleShot(500, settle)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
