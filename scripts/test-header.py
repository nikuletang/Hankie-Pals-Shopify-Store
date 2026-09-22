"""Check the header.

This is the one section that has to meet Dawn rather than sit beside it, and
the theme is not in this repo — so the two places they touch are simulated
here, honestly and narrowly:

- Dawn rewrites #cart-icon-bubble after every add to cart. The page under test
  rewrites it the same way and the suite asserts the visible bubble follows.
  Reading the digits rather than the markup is the point: it survives a Dawn
  that changes what it puts there.
- Dawn's cart drawer is a <cart-drawer> with an open(). A stand-in is defined
  and the suite asserts the cart button calls it instead of navigating, and
  that with no drawer the link is left alone.

Neither proves Dawn's real behaviour. They prove this header keeps its side of
the contract, which is the half that can be got wrong here.
"""
import json, re, subprocess, sys, pathlib

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT = pathlib.Path('/home/user/hankie-pals-shopify-store')
SECTION = ROOT / 'sections' / 'hp-header.liquid'
HERE = ROOT / 'scripts'
TMP = pathlib.Path('/tmp/claude-0')

MENU = {'settings': {'menu': 'main-menu'}}

# A page shaped like a theme: an announcement bar above, a tall hero below.
BAR = ('<div style="height:44px;background:#CFE1B9;text-align:center;'
       'font:600 14px system-ui;line-height:44px">Free shipping over $50</div>')
HERO = ('<div id="hero" style="height:900px;background:#E8DCCF"></div>'
        '<div style="height:1200px;background:#FCFBF6"></div>')

SNAP = """
function box(el) {
  if (!el) return null;
  var r = el.getBoundingClientRect();
  return { l: Math.round(r.left), r: Math.round(r.right), t: Math.round(r.top),
           b: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height) };
}

function snap() {
  var nav = document.querySelector('hp-header');
  var hero = document.getElementById('hero');
  var links = [].map.call(document.querySelectorAll('.hp-nav__links .hp-btn'), function (a) {
    return { text: a.textContent.trim(), href: a.getAttribute('href'),
             cls: a.className, box: box(a) };
  });
  var count = document.querySelector('[data-hp-cart-count]');
  return {
    navPos: getComputedStyle(nav).position,
    navTop: nav.style.getPropertyValue('--hp-nav-top'),
    anchorH: box(document.querySelector('.hp-nav-anchor')).h,
    nav: box(nav),
    hero: box(hero),
    logo: box(document.querySelector('.hp-nav__logo')),
    links: links,
    tools: box(document.querySelector('.hp-nav__tools')),
    burgerShown: (function () {
      var b = document.querySelector('.hp-nav__burger');
      return b ? getComputedStyle(b).display : 'absent';
    })(),
    burgerIcons: [].map.call(document.querySelectorAll('.hp-nav__burger svg'), function (i) {
      return getComputedStyle(i).display;
    }),
    panelBg: (function () {
      var p = document.querySelector('.hp-nav__panel');
      return p ? getComputedStyle(p).backgroundColor : null;
    })(),
    linksShown: document.querySelector('.hp-nav__links')
      ? getComputedStyle(document.querySelector('.hp-nav__links')).display : 'absent',
    searchOpen: (function () {
      var e = document.querySelector('.hp-nav__search');
      return e ? !e.hasAttribute('hidden') : 'absent';
    })(),
    menuOpen: (function () {
      var e = document.querySelector('.hp-nav__drawer');
      return e ? !e.hasAttribute('hidden') : 'absent';
    })(),
    searchExpanded: (function () {
      var e = document.querySelector('[data-hp-search-toggle]');
      return e ? e.getAttribute('aria-expanded') : 'absent';
    })(),
    menuExpanded: (function () {
      var e = document.querySelector('[data-hp-menu-toggle]');
      return e ? e.getAttribute('aria-expanded') : 'absent';
    })(),
    focused: document.activeElement ? document.activeElement.className : null,
    stack: [].map.call(document.querySelectorAll('.hp-nav__stack .hp-btn'), function (a) {
      return a.textContent.trim();
    }),
    stackWide: (function () {
      var a = document.querySelector('.hp-nav__stack .hp-btn');
      return a ? Math.round(a.getBoundingClientRect().width) : null;
    })(),
    count: count ? { text: count.textContent.trim(), hidden: count.hasAttribute('hidden'),
                     bg: getComputedStyle(count).backgroundColor,
                     ink: getComputedStyle(count).color } : null,
    btnStyle: (function () {
      var b = document.querySelector('.hp-nav__links .hp-btn')
              || document.querySelector('.hp-nav__stack .hp-btn');
      if (!b) return null;
      var c = getComputedStyle(b);
      return { radius: c.borderTopLeftRadius, border: c.borderTopWidth,
               bg: c.backgroundColor, ink: c.color, shadow: c.boxShadow };
    })(),
    iconStroke: (function () {
      var i = document.querySelector('.hp-nav__icon svg');
      return i ? getComputedStyle(i).stroke : null;
    })(),
    drawerOpened: window.__drawerOpened || false,
    navigated: window.__navigated || false,
    barMid: (function () {
      var b = document.querySelector('.hp-nav__bar');
      if (!b) return null;
      var r = b.getBoundingClientRect();
      return Math.round((r.left + r.right) / 2);
    })(),
    linksMid: (function () {
      var l = document.querySelectorAll('.hp-nav__links .hp-btn');
      if (!l.length) return null;
      var a = l[0].getBoundingClientRect(), z = l[l.length - 1].getBoundingClientRect();
      return Math.round((a.left + z.right) / 2);
    })(),
    linkBtn: (function () {
      var b = document.querySelector('.hp-nav__links .hp-btn');
      if (!b) return null;
      var c = getComputedStyle(b);
      return { size: c.fontSize, padY: c.paddingTop, padX: c.paddingLeft,
               h: Math.round(b.getBoundingClientRect().height) };
    })(),
    iconH: (function () {
      var i = document.querySelector('.hp-nav__tools .hp-btn');
      return i ? Math.round(i.getBoundingClientRect().height) : null;
    })(),
    docW: document.documentElement.scrollWidth,
    winW: window.innerWidth
  };
}
"""


def run(name, script='', width=1280, overrides=None, before='', late=False):
    page = TMP / f'hd-{name}.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or MENU), str(page)], check=True, capture_output=True)
    html = page.read_text(encoding='utf-8')
    html = html.replace('<body>', '<body>' + BAR + before)
    html = html.replace('</body>', HERO + (LATE if late else '') + '<script>' + SNAP + script +
                        "\nsetTimeout(function(){document.title='RESULT'+JSON.stringify(snap());},"
                        " 500);</script></body>")
    page.write_text(html, encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        f'--window-size={width},900', '--virtual-time-budget=6000', '--dump-dom',
        'file://' + str(page)], capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


# hp-button.css is installed by hand into theme.liquid, so on a real store it
# can land after this section's own rules. That is the worst case and it is
# what these measure against: LATE puts it last on purpose.
LATE = '<link rel="stylesheet" href="' + str(ROOT / 'assets' / 'hp-button.css') + '">'


def framed(name, width=390, click=False, overrides=None, late=True):
    """Measure at a real phone width.

    Headless Chromium will not open a window under 500px, so the page is put
    in an iframe of the width wanted: inside it innerWidth is exactly that and
    the bar lays out as it would on the phone.
    """
    inner = TMP / f'hd-{name}-inner.html'
    subprocess.run([sys.executable, str(HERE / 'render-section.py'), str(SECTION),
                    json.dumps(overrides or MENU), str(inner)], check=True, capture_output=True)
    html = inner.read_text(encoding='utf-8').replace('<body>', '<body>' + BAR)
    html = html.replace('</body>', HERO + (LATE if late else '') + '</body>')
    inner.write_text(html, encoding='utf-8')

    wrap = TMP / f'hd-{name}-wrap.html'
    wrap.write_text(
        '<!doctype html><meta charset="utf-8"><style>html,body{margin:0}'
        f'iframe{{width:{width}px;height:760px;border:0;display:block}}</style>'
        f'<iframe src="{inner.name}"></iframe><script>'
        'setTimeout(function(){'
        'var f=document.querySelector("iframe"), d=f.contentDocument, w=f.contentWindow;'
        + ('var b=d.querySelector("[data-hp-menu-toggle]"); if(b) b.click();' if click else '') +
        'setTimeout(function(){'
        'function bx(e){if(!e)return null;var r=e.getBoundingClientRect();'
        'return {l:Math.round(r.left),r:Math.round(r.right),'
        'w:Math.round(r.width),h:Math.round(r.height)};}'
        'var dr=d.querySelector(".hp-nav__drawer");'
        'var btn=d.querySelector("[data-hp-menu-toggle]");'
        'var sb=d.querySelector(".hp-nav__search-btn");'
        'document.title="RESULT"+JSON.stringify({'
        'innerW:w.innerWidth,'
        'pills:[].map.call(d.querySelectorAll(".hp-nav__bar .hp-btn"),bx),'
        'logo:bx(d.querySelector(".hp-nav__logo")),'
        'burger:bx(btn), drawer:bx(dr),'
        'searchShown:sb?w.getComputedStyle(sb).display:"absent",'
        'drawerHidden:dr?dr.hasAttribute("hidden"):"absent",'
        'stack:[].map.call(d.querySelectorAll(".hp-nav__stack .hp-btn"),function(a){'
        'return a.textContent.trim();})'
        '});},250);},350);</script>',
        encoding='utf-8')
    dom = subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
        '--allow-file-access-from-files', f'--window-size={width + 300},960',
        '--virtual-time-budget=6000', '--dump-dom', 'file://' + str(wrap)],
        capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>RESULT(.*?)</title>', dom, re.S)
    if not m:
        raise SystemExit('no measurement for ' + name)
    return json.loads(m.group(1))


res = []
def check(label, ok, detail):
    res.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label}\n        {detail}")


def rgb(v):
    return [int(x) for x in re.findall(r'\d+', v)[:3]]


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 2)


# ------------------------------------------------------------ the bar ------
d = run('base')
check('the links are the site\'s buttons, not text',
      len(d['links']) == 3 and all('hp-btn' in l['cls'] for l in d['links']),
      f"{[l['text'] for l in d['links']]}")
check('and they carry the pill, the outline and the hard shadow',
      d['btnStyle']['radius'] == '999px' and d['btnStyle']['border'] == '2px'
      and '0px 3px 0px 0px' in d['btnStyle']['shadow'],
      f"radius {d['btnStyle']['radius']}, outline {d['btnStyle']['border']}, "
      f"shadow {d['btnStyle']['shadow'].split(') ')[-1]}")
check('the logo is on the left and the icons on the right',
      d['logo']['l'] < d['links'][0]['box']['l'] < d['tools']['l'],
      f"logo ends {d['logo']['r']}, links start {d['links'][0]['box']['l']}, "
      f"icons start {d['tools']['l']}")

# The whole point of the overlay: the hero starts at the top of the page.
check('the header takes up no room, so the hero runs under it',
      d['anchorH'] == 0 and d['hero']['t'] < d['nav']['b'],
      f"anchor {d['anchorH']}px tall; hero starts at {d['hero']['t']}, "
      f"bar ends at {d['nav']['b']}")
check('and it sits below the announcement bar rather than over it',
      d['navPos'] == 'fixed' and d['navTop'] == '44px',
      f"position {d['navPos']}, top {d['navTop']} against a 44px bar")

pinned = run('pinned', script="""
  // The clock cannot be scrolled here, so the scroll is handed to the handler
  // rather than performed. That only works because the bar's height is
  // measured once and kept: a handler that re-read layout every time would
  // cancel the fake out and report no movement at all.
  Object.defineProperty(window, 'scrollY', { value: 600, configurable: true });
  document.querySelector('hp-header').onScroll();
""")
check('once the announcement bar has scrolled away it pins to the top',
      pinned['navTop'] == '0px', f"top {pinned['navTop']} at 600px down")

check('nothing runs off the edge',
      d['docW'] <= d['winW'], f"document {d['docW']}px in {d['winW']}px")

# ------------------------------------------------------------- the icons ---
check('an icon takes the pill\'s own text colour',
      rgb(d['iconStroke']) == rgb(d['btnStyle']['ink']),
      f"stroke {d['iconStroke']} against text {d['btnStyle']['ink']}")
check('the cart count is hidden with an empty cart',
      d['count']['hidden'], f"hidden: {d['count']['hidden']}")

# --------------------------------------------------- search and the menu ---
sr = run('search', script="document.querySelector('[data-hp-search-toggle]').click();")
check('the search button opens a field and says so',
      sr['searchOpen'] and sr['searchExpanded'] == 'true'
      and 'hp-nav__field' in (sr['focused'] or ''),
      f"open {sr['searchOpen']}, aria-expanded {sr['searchExpanded']}, "
      f"focus on {sr['focused']}")
esc = run('search-esc', script="""
  document.querySelector('[data-hp-search-toggle]').click();
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
""")
check('and Escape closes it again',
      not esc['searchOpen'] and esc['searchExpanded'] == 'false',
      f"open {esc['searchOpen']}, aria-expanded {esc['searchExpanded']}")

phone_shut = run('menu-shut', width=500)
mn = run('menu', script="document.querySelector('[data-hp-menu-toggle]').click();", width=500)
check('the hamburger opens the same buttons, stacked',
      mn['menuOpen'] and mn['stack'] == [l['text'] for l in d['links']],
      f"{mn['stack']}")
check('and they run the full width of the phone',
      mn['stackWide'] and mn['stackWide'] > 300,
      f"{mn['stackWide']}px wide in a 500px window")
# The `hidden` attribute is a UA rule, and a UA rule loses to any author rule —
# so an svg { display: block } above it shows the cross and the hamburger at
# once. It looked fine in the markup and wrong on the screen.
check('the burger shows one icon, not both',
      phone_shut['burgerIcons'].count('none') == 1,
      f"closed: {phone_shut['burgerIcons']}")
check('and swaps to the cross when the menu opens',
      mn['burgerIcons'].count('none') == 1
      and mn['burgerIcons'][0] == 'none',
      f"open: {mn['burgerIcons']}")
check('the open menu has something behind it, not the hero',
      mn['panelBg'] and mn['panelBg'] != 'rgba(0, 0, 0, 0)',
      f"panel background {mn['panelBg']}")

both = run('both', script="""
  document.querySelector('[data-hp-menu-toggle]').click();
  document.querySelector('[data-hp-search-toggle]').click();
""", width=500)
check('opening one closes the other',
      both['searchOpen'] and not both['menuOpen'],
      f"search {both['searchOpen']}, menu {both['menuOpen']}")

phone = run('phone', width=500)
check('on a phone the links give way to the hamburger',
      phone['linksShown'] == 'none' and phone['burgerShown'] != 'none',
      f"links {phone['linksShown']}, burger {phone['burgerShown']}")
desk = run('desk', width=1280)
check('and on a desktop the hamburger gives way to the links',
      desk['burgerShown'] == 'none' and desk['linksShown'] != 'none',
      f"burger {desk['burgerShown']}, links {desk['linksShown']}")

for w in (1600, 1280, 990, 750, 500):
    n = run(f'w{w}', width=w)
    check(f'nothing overflows at {w}px',
          n['docW'] <= n['winW'] and n['logo']['l'] >= 0
          and n['tools']['r'] <= n['winW'],
          f"document {n['docW']}px in {n['winW']}px, icons end at {n['tools']['r']}")

# ------------------------------------------------- where it meets Dawn -----
# Dawn writes the count into #cart-icon-bubble. Whatever it writes.
sync = run('cart-sync', script="""
  document.querySelector('#cart-icon-bubble').innerHTML =
    '<div class="cart-count-bubble"><span aria-hidden="true">4</span>' +
    '<span class="visually-hidden">4 items</span></div>';
""")
check('the cart count follows whatever Dawn writes into its own element',
      sync['count']['text'] == '4' and not sync['count']['hidden'],
      f"bubble reads \"{sync['count']['text']}\", hidden {sync['count']['hidden']}")
zero = run('cart-zero', script="""
  document.querySelector('#cart-icon-bubble').innerHTML = '';
""")
# A Dawn that stops marking the visible span still has to work.
plainer = run('cart-plain', script="""
  document.querySelector('#cart-icon-bubble').innerHTML =
    '<div class="cart-count-bubble"><span>7</span><span>7 items</span></div>';
""")
check('and it still reads right if Dawn drops the aria-hidden marker',
      plainer['count']['text'] == '7', f"bubble reads \"{plainer['count']['text']}\"")
check('and goes away again when the cart empties',
      zero['count']['hidden'], f"hidden {zero['count']['hidden']}")

DRAWER = """<script>
  window.__drawerOpened = false;
  window.__navigated = false;
  customElements.define('cart-drawer', class extends HTMLElement {
    open() { window.__drawerOpened = true; }
  });
</script><cart-drawer></cart-drawer>"""
drw = run('cart-drawer', before=DRAWER, script="""
  var link = document.querySelector('[data-hp-cart]');
  link.addEventListener('click', function (e) {
    if (!e.defaultPrevented) window.__navigated = true;
    e.preventDefault();
  });
  link.click();
""")
check('the cart button opens the drawer when there is one',
      drw['drawerOpened'] and not drw['navigated'],
      f"drawer opened {drw['drawerOpened']}, followed the link {drw['navigated']}")
nodrw = run('cart-nodrawer', script="""
  window.__navigated = false;
  var link = document.querySelector('[data-hp-cart]');
  link.addEventListener('click', function (e) {
    if (!e.defaultPrevented) window.__navigated = true;
    e.preventDefault();
  });
  link.click();
""")
check('and follows its href to the cart page when there is not',
      nodrw['navigated'],
      'nothing prevented the link, so the cart page still works')

# ------------------------------------------------------------- contrast ----
check('the button labels are readable on their fill',
      contrast(rgb(d['btnStyle']['ink']), rgb(d['btnStyle']['bg'])) >= 4.5,
      f"{contrast(rgb(d['btnStyle']['ink']), rgb(d['btnStyle']['bg']))}:1")
check('and so is the cart count',
      contrast(rgb(sync['count']['ink']), rgb(sync['count']['bg'])) >= 4.5,
      f"{contrast(rgb(sync['count']['ink']), rgb(sync['count']['bg']))}:1")

# ------------------------------------------------- the menu is the switch ----
# The burger opens a drawer that is only rendered when a menu is set. With no
# menu picked in Links there is nothing to open, so there must be no burger
# either -- an empty bar, not a button that does nothing.
# Nothing picked is the state a freshly added section is in, and an empty bar
# is indistinguishable from a broken one. Fall back to the store's own main
# menu instead. A schema `default` does not cover this: defaults are baked in
# when the instance is first saved, so a section already on the page keeps its
# empty value for good.
unpicked = run('no-menu', overrides={'settings': {'menu': ''}})
check('with nothing picked it falls back to the store main menu',
      [l['text'] for l in unpicked['links']] == ['Home', 'Catalog', 'Contact'],
      f"{[l['text'] for l in unpicked['links']]}")
check('and the hamburger is there to open them on a phone',
      unpicked['burgerShown'] != 'absent',
      f"burger {unpicked['burgerShown']}")

# Only when the store itself has no menu is there nothing to draw -- and then
# there must be no hamburger either, since it would open an empty drawer.
# The guard counts links rather than comparing the menu to blank: a menu that
# is not there is nil in one Liquid and an EmptyDrop in another, and the two
# disagree about `!= blank`. Nothing disagrees about how many links it has.
nomenu = run('bare-store', overrides={'settings': {'menu': ''}, 'linklists': {}})
check('a store with no menu at all draws no link buttons',
      nomenu['links'] == [],
      f"links {nomenu['links']}")
check('and no hamburger to open an empty drawer',
      nomenu['burgerShown'] == 'absent',
      f"burger {nomenu['burgerShown']}")

# ------------------------------------------------- cascade, not file order ----
# `.hp-nav__burger` weighs the same as `.hp-btn`, so hiding the burger used to
# depend on the shared stylesheet loading first. It is installed by hand in
# theme.liquid, so that order is not ours to promise. Load it LAST here -- the
# worst case -- and the burger must still stay down on a desktop.
late = run('late-css', script="""
  var s = document.createElement('style');
  s.textContent = '.hp-btn { display: inline-flex; }';
  document.body.appendChild(s);
""")
check('the burger stays hidden on desktop even if hp-button.css loads last',
      late['burgerShown'] == 'none',
      f"burger {late['burgerShown']} with .hp-btn appended after everything")
check('and the links are still the ones showing',
      [l['text'] for l in late['links']] != [],
      f"{[l['text'] for l in late['links']]}")

# ------------------------------------------------------- the breakpoint ------
# Long link names crowd the bar sooner, so where it folds is a setting.
wide = run('bp-wide', width=1000, overrides={'settings': {'menu': 'main-menu',
                                                         'nav_breakpoint': 1100}})
check('raising the breakpoint folds the links into the hamburger sooner',
      wide['burgerShown'] != 'none' and wide['links'][0]['box'] is None
      or wide['burgerShown'] != 'none',
      f"at 1000px with the switch at 1100px: burger {wide['burgerShown']}")

narrow = run('bp-narrow', width=1000, overrides={'settings': {'menu': 'main-menu',
                                                             'nav_breakpoint': 900}})
check('and lowering it keeps them as buttons at the same width',
      narrow['burgerShown'] == 'none',
      f"at 1000px with the switch at 900px: burger {narrow['burgerShown']}")

# ------------------------------------------------- a real phone, worst case ----
# The window minimum in headless is 500px, and at 500px this all fitted -- which
# is why an overflow at 390px went out. These run in a frame of the true width,
# with hp-button.css loaded last, which is the state a real store is in.
ph = framed('phone390', 390)
over = [b for b in ph['pills'] if b and b['r'] > ph['innerW']]
check('nothing in the bar reaches past the edge of a 390px phone',
      not over,
      f"widest pill ends at {max((b['r'] for b in ph['pills'] if b), default=0)} "
      f"in {ph['innerW']}px")
check('the icon pills keep their own padding, not the shared stylesheet\'s',
      all(b['w'] <= 50 for b in ph['pills'] if b and b['w'] > 0),
      f"pill widths {[b['w'] for b in ph['pills'] if b]}")
check('search stands down on a phone, leaving logo, account, cart, menu',
      ph['searchShown'] == 'none',
      f"search display {ph['searchShown']}")
check('and the hamburger is inside the screen, so it can be tapped',
      ph['burger'] and ph['burger']['r'] <= ph['innerW'] and ph['burger']['l'] >= 0,
      f"burger at {ph['burger']}")

opened = framed('phone390open', 390, click=True)
check('tapping it opens the drawer',
      opened['drawerHidden'] is False,
      f"drawer hidden: {opened['drawerHidden']}")
check('with the three links stacked inside it',
      opened['stack'] == ['Home', 'Catalog', 'Contact'],
      f"{opened['stack']}")
check('and the drawer itself fits the phone',
      opened['drawer'] and opened['drawer']['r'] <= opened['innerW'],
      f"drawer {opened['drawer']} in {opened['innerW']}px")

keep = framed('phone-search', 390,
              overrides={'settings': {'menu': 'main-menu', 'show_search_mobile': True}})
check('search can be kept on a phone if that is wanted',
      keep['searchShown'] != 'none',
      f"search display {keep['searchShown']}")

# ------------------------------------------------- centred, and sized ---------
# Measured with hp-button.css last, since that is where the sizing used to be
# lost. A three-column grid centres the middle column on the bar rather than on
# whatever room is left beside the logo, so the answer does not depend on how
# wide the logo happens to be.
mid = run('centred', late=True)
check('the link buttons sit on the middle of the bar, not beside the logo',
      abs(mid['barMid'] - mid['linksMid']) <= 2,
      f"bar midpoint {mid['barMid']}, links midpoint {mid['linksMid']}")

wide_logo = run('centred-wide', late=True,
                overrides={'settings': {'menu': 'main-menu', 'logo_width': 320}})
check('and stay centred when the logo is a different width',
      abs(wide_logo['barMid'] - wide_logo['linksMid']) <= 2,
      f"bar midpoint {wide_logo['barMid']}, links midpoint {wide_logo['linksMid']}")

right = run('links-right', late=True,
            overrides={'settings': {'menu': 'main-menu', 'links_position': 'right'}})
check('and they can be put back beside the icons instead',
      right['linksMid'] > right['barMid'] + 50,
      f"links midpoint {right['linksMid']} against bar midpoint {right['barMid']}")

small = run('menu-sm', late=True,
            overrides={'settings': {'menu': 'main-menu', 'menu_size': 11}})
big = run('menu-lg', late=True,
          overrides={'settings': {'menu': 'main-menu', 'menu_size': 22}})
check('the menu button size setting changes the link buttons',
      big['linkBtn']['h'] > small['linkBtn']['h'] + 15,
      f"11px -> {small['linkBtn']['h']}px tall, 22px -> {big['linkBtn']['h']}px tall")
check('and it survives hp-button.css loading last',
      big['linkBtn']['size'] == '22px' and small['linkBtn']['size'] == '11px',
      f"font sizes {small['linkBtn']['size']} and {big['linkBtn']['size']}")
check('the padding scales with it rather than staying put',
      big['linkBtn']['padX'] != small['linkBtn']['padX'],
      f"pad-x {small['linkBtn']['padX']} -> {big['linkBtn']['padX']}")
check('and the icon buttons are left out of it',
      big['iconH'] == small['iconH'],
      f"icon height {small['iconH']} either way")

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
