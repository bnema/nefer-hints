"""Six colour schemes (4 dark, 2 light). No colour is near #FF00FF (checked)."""
def _h(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
THEMES = {
 'night': dict(bg='#1a1b26', fg='#c0caf5', c=['#15161e','#f7768e','#9ece6a','#e0af68','#7aa2f7','#bb9af7','#7dcfff','#a9b1d6','#414868','#f7768e','#9ece6a','#e0af68','#7aa2f7','#bb9af7','#7dcfff','#c0caf5']),
 'solar-dark': dict(bg='#002b36', fg='#839496', c=['#073642','#dc322f','#859900','#b58900','#268bd2','#a066b0','#2aa198','#eee8d5','#586e75','#cb4b16','#586e75','#657b83','#839496','#6c71c4','#93a1a1','#fdf6e3']),
 'mono-dark': dict(bg='#101010', fg='#d0d0d0', c=['#000000','#cc0000','#4e9a06','#c4a000','#3465a4','#8a5fa8','#06989a','#d3d7cf','#555753','#ef2929','#8ae234','#fce94f','#729fcf','#ad7fa8','#34e2e2','#eeeeec']),
 'warm-dark': dict(bg='#282828', fg='#ebdbb2', c=['#282828','#cc241d','#98971a','#d79921','#458588','#b16286','#689d6a','#a89984','#928374','#fb4934','#b8bb26','#fabd2f','#83a598','#d3869b','#8ec07c','#ebdbb2']),
 'paper': dict(bg='#fafafa', fg='#383a42', c=['#383a42','#e45649','#50a14f','#c18401','#4078f2','#a626a4','#0184bc','#a0a1a7','#4f525e','#e06c75','#98c379','#e5c07b','#61afef','#c678dd','#56b6c2','#ffffff']),
 'solar-light': dict(bg='#fdf6e3', fg='#657b83', c=['#073642','#dc322f','#859900','#b58900','#268bd2','#6c71c4','#2aa198','#eee8d5','#002b36','#cb4b16','#586e75','#657b83','#839496','#6c71c4','#93a1a1','#fdf6e3']),
}
DARK = ['night', 'solar-dark', 'mono-dark', 'warm-dark']
LIGHT = ['paper', 'solar-light']
for _n, _t in THEMES.items():
    for _c in [_t['bg'], _t['fg']] + _t['c']:
        r, g, b = _h(_c)
        assert not (abs(r - 255) < 60 and g < 60 and abs(b - 255) < 60), (_n, _c)
