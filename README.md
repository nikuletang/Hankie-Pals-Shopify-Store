# Hankie Pals Shopify Store

Custom [Online Store 2.0](https://shopify.dev/docs/storefronts/themes/architecture/sections)
sections for the Totterful / Hankie Pals storefront. The store runs **Dawn**.

The folder layout matches Shopify's own theme structure (`sections/`, and
`snippets/`, `assets/` etc. as they appear), so this repo can grow into the full
theme later and be connected through Shopify's GitHub integration without
anything moving.

## Sections

| File | Shows up in the editor as | What it is |
| --- | --- | --- |
| [`sections/problem-cards.liquid`](sections/problem-cards.liquid) | **Problem blobs** | Eyebrow pill, display heading, three organic blob cards |
| [`sections/pals-picker.liquid`](sections/pals-picker.liquid) | **Meet the Pals** | Character picker: choosing a Pal swaps the photo, tint, copy and buy button |
| [`sections/solution-tabs.liquid`](sections/solution-tabs.liquid) | **Solution tabs** | Three feature cards; picking one crossfades the large image beside them |
| [`sections/hero-split.liquid`](sections/hero-split.liquid) | **Split hero** | Two panels with independent backgrounds: copy and an offset CTA left, a portrait right. Stays side by side on a phone unless set to stack |
| [`sections/variant-grid.liquid`](sections/variant-grid.liquid) | **Variant grid** | Full-width cards, one per variant of a single product, with a hover image swap |
| [`sections/why-choose.liquid`](sections/why-choose.liquid) | **Why choose us** | A heading over a row of value props, each with an icon drawn in SVG rather than uploaded |
| [`sections/section-divider.liquid`](sections/section-divider.liquid) | **Section divider** | A shaped edge — torn, zigzag, wave, scallop, slant, arch — to sit between two sections |
| [`sections/marquee.liquid`](sections/marquee.liquid) | **Scrolling marquee** | A band of text and images sliding past, with filled or outlined lettering |
| [`sections/pal-reveal.liquid`](sections/pal-reveal.liquid) | **Pal reveal** | A Pal that grows on scroll until its body becomes the next section |
| [`sections/pal-panel.liquid`](sections/pal-panel.liquid) | **Pal panel** | A domed Pal-shaped panel that rises over the pinned section above and holds the copy |
| [`sections/hp-footer.liquid`](sections/hp-footer.liquid) | **Totterful footer** | Brand, menu columns, policies. Goes in the footer section group, so it is on every page |

Click a filename above, then use the **copy icon** in the toolbar over the code
to take the whole file.

**Do not use raw.githubusercontent.com links on this repo.** It is private, and
raw URLs do not carry your browser session, so a bare raw link returns 404 for
everybody including you. The Raw button inside GitHub works, because GitHub
appends a short-lived token to it; a copied raw URL stops working once that
token expires. Use the copy icon instead.

## Installing a section by hand

1. Shopify admin → **Online Store → Themes**. Duplicate the theme first and work
   on the copy.
2. **⋯ → Edit code** → **Sections → Add a new section**. Name it to match the
   filename without the extension (`problem-cards`).
3. Delete the starter contents, paste the file from this repo, **Save**.
4. **Customize → Add section** on the home page and pick it by the name in the
   table above. It arrives already filled in — each section carries a `presets`
   block with the real copy and colours.

Section settings live in the theme, not in these files, so re-pasting an updated
file keeps the images, copy and colours already set in the editor.

## The mailing list

The Pal reveal's last act is a sign-up rather than a button. It is Shopify's own
`{% form 'customer' %}` with a hidden `contact[tags]` of `newsletter`, which is
the list Shopify Email sends to — no app, nothing to connect, and the address
becomes a customer the moment it is submitted. The form posts to `/contact` and
comes back with `?customer_posted=true`, which is what `form.posted_successfully?`
reads.

The button is still there under **What comes last → Button**. The branch tests
`s.cta_style == 'button'` rather than `== 'email'`, so a section saved before the
setting existed — where the value is nil — falls to the sign-up, which is the
point of the change.

Three things a form gets wrong that a page never shows you, all asserted in
`scripts/test-signup.py`:

- **16px on the field is a floor, not a preference.** Below it, iOS Safari zooms
  the page in when the field takes focus and does not zoom back out.
- **A placeholder is the contrast that gets missed.** Firefox dims placeholders
  on its own, so the rule pins `opacity: 1` and the suite measures the computed
  `::placeholder` colour rather than the declared one.
- **The label has to be hidden, not removed.** `display: none` takes it out of
  the accessibility tree as well as off the screen; the clip-path version leaves
  it in one and not the other, and the suite checks both.

The renderer grew a `form` object for this, passed through from the overrides,
because the posted and refused states are not reachable by rendering the page
normally.

    python3 scripts/test-signup.py

Twenty-six cases: the form tag, the field name and tag, the scoped ids, required
and autocomplete, the hidden label, 16px and a 44px target, the success and
error states with the typed address kept, the button still available, an unset
setting landing on the sign-up, and no overflow at four widths.

## Installing the footer

The footer is not installed like the others, and the difference is the point.

Dawn renders it through a **section group**: `layout/theme.liquid` contains
`{% sections 'footer-group' %}`, and `sections/footer-group.json` lists what is
inside. A section group renders on *every* page — home, product, collection,
cart, search, 404, policy pages — so anything in it is site-wide with no
per-template work and nothing to keep in step.

1. **⋯ → Edit code** → **Sections → Add a new section**, name it `hp-footer`,
   paste the file, **Save**.
2. **Customize**, scroll to the **Footer** area at the bottom of the left panel,
   **Add section**, pick *Totterful footer*.
3. Hide Dawn's own footer with the eye icon rather than deleting it, so it is
   one click to get back.

The schema carries `"enabled_on": { "groups": ["footer"] }`, which is what makes
this structural rather than a thing to remember: the section is offered *only*
in the footer group, so it cannot be added to a single template by accident and
it does not clutter the home page's section list. `scripts/test-footer.py`
asserts that line is there, because a footer that looks right but was installed
on one page is invisible from the page itself.

If Customize shows no Footer area to add sections to, the theme predates section
groups (Dawn before 2021) and `sections/footer.liquid` is edited directly
instead — same design, different install.

Links come from Shopify menus, edited in **Content → Menus**. Policy links come
from `shop.policies`, so each appears as soon as that policy has content in
**Settings → Policies** — a policy with nothing in it is not in the array, so
the footer never links to an empty page.

    python3 scripts/test-footer.py

Twenty-three cases: the `enabled_on` restriction and the preset; menu and policy
links rendering with real hrefs; an unset menu drawing no empty list; the column
count following the blocks; no overflow at five widths; two-up columns on a
phone; contrast on links, headings and the copyright line; and a 24px minimum
tap target — an inline link's box is the height of its text, so a 15px link is
an 18px target however much line-height it is given, which is what the first
run of this suite caught.

## Installing the button

Four sections draw a button, and they all use the same one. It lives in
[`assets/hp-button.css`](assets/hp-button.css) rather than inside any of them,
so it is installed once:

1. **⋯ → Edit code** → **Assets → Add a new asset → Create a blank file**, name
   it `hp-button.css`, paste the file from this repo, **Save**.
2. That is enough for the custom sections: each one links the stylesheet itself.

To get the same button on the pages Shopify draws — the product page, the cart
drawer, checkout, the newsletter sign-up — also add
[`assets/hp-button-dawn.css`](assets/hp-button-dawn.css) as a second asset, and
load it from **Layout → theme.liquid** with this line as the last thing before
`</head>`:

    {{ 'hp-button-dawn.css' | asset_url | stylesheet_tag }}

It has to come last, because it is overriding Dawn's own rules. That file is
separate on purpose: Dawn builds its buttons out of pseudo elements and its own
custom properties, and those change between Dawn versions, so if anything looks
wrong afterwards, delete that one line and nothing else on the site changes.

Two things about Shopify's own buttons are worth knowing before changing that
file, because both cost a round trip on the live store:

- **Add to cart is `button--secondary` whenever the dynamic checkout button is
  switched on.** So the shop's main action picks up whatever quiet treatment
  `--secondary` gets and comes out as an empty outline. `.product-form__submit`
  fills it back in, later in the file and at the same weight.
- **Shopify injects the styles for Buy it now at runtime**, which puts them
  after anything the theme loads, however early the theme loads it. Matching
  Dawn's specificity is not enough — the class is doubled to outdo it, and the
  properties Shopify sets itself are forced. That is the one place `!important`
  is the right tool rather than a shortcut.

`scripts/test-button-dawn.py` covers both, against a stand-in for Dawn rather
than Dawn itself: the theme is not in this repo and the store is not reachable
from here, so the page carries Dawn's product-form markup, a stylesheet that
behaves like Dawn's, and a script that injects the payment-button styles the
way Shopify does. It tests the override mechanics, which is what both of those
bugs were; it would not catch a Dawn version that renames a class.

    python3 scripts/test-button-dawn.py

## Changing the button

Change `assets/hp-button.css` and every button on the site changes with it —
that is the whole point of it being one file. What each section is allowed to
set is the fill, the text colour, and the colour of the outline and shadow;
shape, weight, size steps, shadow behaviour and states are not per-section
decisions and are not exposed in the editor.

A new section does not inherit the button by being new. It needs two lines —
the stylesheet link beside `{% endstyle %}`, and `hp-btn` on the element — and
then it is bound by everything above. The suite is what makes that reliable: it
finds the sections with buttons rather than being told them, so a section added
later is held to the same rules without anyone remembering to add it. A call to
action is a section offering a label and a link for one, which is why
solution-tabs' tab and why-choose's text link are left alone — they are controls,
and turning them into pills would be worse, not more consistent.

`scripts/test-button.py` renders every section with a button against the real stylesheet
and compares the computed style of every button to every other one, so a
section that starts drawing its own button again fails the build rather than
quietly shipping. Its first assertion is that the stylesheet actually loaded:
without it, every button matches every other one at the browser's defaults and
every comparison afterwards passes for nothing.

    python3 scripts/test-button.py

Twenty-four cases: every section with a button linking the stylesheet, putting
its button on the shared class, and not redrawing it underneath; then radius, outline, capitalisation, tracking, weight and typeface
identical across every section; every shadow hard, unblurred and straight down
in the outline's colour; the label clearing 4.5:1 on every fill in use; the
press travelling exactly the height of the shadow it lands on; the three sizes
stepping in the right direction with shadows to match; the ghost and sold-out
states; and reduced motion.

## Two things to know before editing these files

**Dawn sets `html { font-size: calc(var(--font-body-scale) * 62.5%) }.** One rem
is 10px on this store, not 16px. Anything sized in `rem` renders at 62.5% of
what it looks like elsewhere — 17px body copy comes out at 10.6px. Size things
in `px` here. The theme's type sliders are still honoured, explicitly, by
multiplying through `--font-body-scale` and `--font-heading-scale`.

**Type and weight come from the theme, colour does not.** Sections read
`--font-heading-family`, `--font-heading-weight` and `--font-body-family`, so
they pick up whatever faces the theme is set to; the values after each `var()`
are only fallbacks. Colours are section settings instead, so a section can be
re-tinted per page without touching global styles.

## House rules for anything added here

- Prefix every selector with the section's own class (`.hp-problem`, …) and pass
  per-instance values in as inline custom properties. Nothing should be able to
  reach another section.
- Everything visible in the design is editable in the theme editor.
- Repeatable content goes in blocks, not numbered settings, so it can be
  reordered and removed.
- No JavaScript unless the interaction genuinely needs it.
- Check every section at desktop, tablet and mobile before committing.

## Meet the Pals: one product, one variant per character

The section takes a single product. Each Pal block finds its own variant by
matching the Pal's **name** against the variant's option value, so naming the
variants after the characters is the whole setup — no variant IDs to paste. A
block only needs the *Variant name* override when the variant is spelled
differently from the display name.

Consequences worth knowing:

- Sold-out state is per variant, so a Pal greys out on its own when it runs out.
- Adding two Pals is two lines of the same product, which is what makes
  collecting work.
- With no product attached, or no matching variant, each Pal falls back to its
  own link — which is how the section works before launch, pointed at the
  waitlist.

The buy button posts to the cart and opens the theme's cart drawer without
leaving the page. If the theme has no `cart-drawer`, or JavaScript is off, the
form submits normally and lands on the cart page. Nothing is conditional on the
script running.

## Testing Liquid without a store

    pip install python-liquid
    python3 scripts/test-variant-resolution.py

The variant grid resolves each card's variant in Liquid, and that logic cannot be
checked by rendering HTML. The test lifts the `{%- liquid -%}` block straight out
of the section — not a Python restatement of it — and runs it against mock
products: exact names, wrong case, padded names, a first option against a
combined title, positional fallback, unknown names, and cards beyond the variant
count.

It earned its keep immediately, catching

    assign a11y_name = card_title | append: ', ' | append: variant.price | money

where `money` receives the whole concatenated sentence rather than the price,
because Liquid filters chain left to right. Nothing about the rendered page would
have looked wrong; only the screen-reader label was broken.

## Render a section without a store

`scripts/render-section.py` turns any section here into a standalone HTML page,
using the schema's own defaults for settings and the first preset for blocks —
which is what Shopify builds when the section is added from the theme editor.

    python3 scripts/render-section.py sections/why-choose.liquid '{}' /tmp/out.html

The third argument is optional JSON that overrides settings and blocks, so a
layout can be checked under a setting nobody has saved yet:

    python3 scripts/render-section.py sections/why-choose.liquid \
      '{"settings": {"icon_backdrop": "blob", "columns": "3"}}' /tmp/out.html

Open it in a headless browser and measure it rather than judging by eye. This
is what caught the icons rendering at 290px instead of 56px: two classes on one
element, same specificity, and the one that happened to be written later won.

One difference from the real store worth knowing: Shopify counts nil as blank,
and python-liquid does not, so the script passes an unset setting as an empty
string. Both are blank, so every `!= blank` branch takes the side it takes on
the store.

## Test a section that draws a shape

`scripts/test-divider.py` screenshots each divider shape and reads the pixels
back with Pillow: a divider that paints nothing still renders a perfectly
plausible coloured band, so nothing short of looking at the pixels proves the
shape is there.

    pip install Pillow
    python3 scripts/test-divider.py

Fifteen cases: every shape painted and ending in the lower colour, the peak
count matching the setting in both repeat modes, the count holding when the
viewport halves, the band measuring the height asked for, the colours swapping
when it points up, and the torn tile having no visible seam.

## Test a section's behaviour

`scripts/test-reveal.py` drives the why-choose reveal in headless Chromium and
checks every path it has to survive: in view on load, still hidden below the
fold, the observer reporting an entry, replay on and off, reduced motion, no
IntersectionObserver, the theme editor tearing the section out and putting it
back, and each motion style's start state.

    python3 scripts/test-reveal.py

Two traps it is built around, both of which produced false results first:

- Chromium under `--virtual-time-budget` renders about **two animation frames**,
  so a computed value read mid-transition still reports the *start* of it. Every
  assertion here cuts the transitions first, so the cascade resolves straight to
  its target.
- For the same reason no rendering lifecycle runs after a programmatic scroll,
  so the browser never recomputes intersection. Scroll-triggered timing is the
  browser's job; what the suite checks is this element's handling of an entry.

## Decoration that must not touch the content

The pebbles in the top corners of **Meet the Pals** are the pattern for any
shape that decorates a band of text. Three rules, all of them learned by
measuring:

- **Place a bleeding shape by its inner edge, not by its own width.** Offsetting
  by a share of the shape (`left: calc(var(--w) * -0.34)`) means a bigger shape
  reaches further into the content — and the heading is closest to the margin at
  exactly the sizes where the shape is largest. `left: calc(<edge> - var(--w))`
  pins the inner edge instead and lets the overhang grow off-screen, which is
  where it should go.
- **The margin closes faster than the window does.** Headings here only shrink
  from 52px to 36px across the whole desktop range, so the space beside them
  falls away faster than a plain `vw` gives up. The edge is
  `calc(12vw - 44px)`, which holds a flat ~36px of clearance from 750px to
  1200px and opens out above that.
- **Measure the lines, not the element.** `.hp-pals__heading` is `28ch` wide and
  centred, so its box runs nearly edge to edge while the words sit in the middle
  of it. Asserting against the box reports an overlap nobody can see and would
  push the decoration off the screen to satisfy it. The suite takes
  `document.createRange().selectNodeContents(el).getClientRects()` and asserts
  against the line boxes, with a floor of 24px so a later tweak cannot creep
  back up to the text.

The picker row uses `justify-content: safe center` on a horizontally scrolling
flex row. Plain `center` pushes the overflow out of the *left* edge, where no
amount of scrolling reaches it; `safe` centres while the Pals fit and falls back
to the start when they do not. A browser that does not know the keyword drops
the declaration, so the `flex-start` above it stays as the floor.

    python3 scripts/test-pals-picker.py

Twenty-seven cases: both pebbles in their corners and hanging off the edge,
behind the content, unclickable, 24px clear of every line of text at seven
widths, gone below 750px, the band clipping instead of widening the page,
reduced motion, and the picker row centred at three phone widths while a row of
six Pals still starts at the first one.

## A shadow on a shape that is not a rectangle

The Pal panel's dome is a `border-radius`, not a clip path, and `box-shadow`
follows `border-radius` — so the shadow traces the dome with nothing extra to
draw. Two consequences worth keeping:

- **The offset is negative.** The panel rises over the section above it, so the
  shadow goes up. A shadow pointing down would put it on the section it is
  covering, which is backwards.
- **The flat bottom edge cannot leak.** An outer `box-shadow` is clipped to
  outside the border box, so none of it reaches the next section however far the
  strength is turned up. `scripts/test-pal-panel.py` measures that rather than
  trusting it, at 60%.

The ears need their own. They stand above the dome as separate elements, so
without one the panel lifts off the page and they stay pasted flat to it — at
exactly the point the eye goes to.

The shadow is measured by differencing two frames of the same page, one with it
and one without, rather than by comparing it to the colour behind it: what is
behind depends on where the pin has got to, and the difference between the two
frames is the shadow and nothing else. The bottom-edge case scrolls nothing,
because **Chromium does not repaint after a programmatic scroll** under a
virtual time budget and the frame comes back blank — the section above is set
to zero height instead, so the whole panel starts in view.

## Check a schema before pasting it in

It knows the rules Shopify only tells you about one at a time, on paste:

- a range may have at most **101 steps** between its min and max
- a range's **unit is at most 3 characters** — `px/s` is rejected, `px` is fine
- the max must be reachable from the min in whole steps
- a default must sit inside its own range, and a select's default must be one
  of its options
- no duplicate setting ids, and nothing interpolated into CSS without a
  `| default:`


    python3 scripts/check-schemas.py

Shopify validates a section's schema on save, reports only the first failure, and
only once the file is in the theme — so a bad schema costs a round trip to find
and another to fix. The checker catches what can be caught locally:

- range settings over Shopify's 101-step limit, or whose max is unreachable from
  the min in whole steps, or whose default falls outside the range
- select defaults that are not one of the options
- duplicate setting ids
- settings read in the body that no setting declares
- settings interpolated into CSS without a `| default:` fallback, per the note
  below. **In CSS only** — inside `{% style %}` or a `style="…"` attribute,
  where a nil leaves `--x: ;` and voids the declaration. In text a nil renders
  as nothing, which is what an optional setting is for, and demanding
  `| default: ''` for that just teaches you to ignore the warning

## Adding a setting to a section that is already on a page

A section instance stores only the settings it was saved with. Add a new setting
to the schema and existing instances have no value for it, so `section.settings`
returns nil for that key — the schema default does not retroactively fill it in.

Interpolated straight into CSS, that nil is silently destructive:

    --wash-spread: {{ s.wash_spread }}px;    ->  --wash-spread: px;
    inset: calc(var(--wash-spread) * -1);    ->  invalid, declaration dropped

An absolutely positioned element then has no offsets and collapses to zero by
zero. Nothing renders, nothing errors, and the theme editor shows the setting at
what looks like a sensible value.

So every `{{ s.something }}` that lands in CSS carries a `| default:` matching
its schema default. A CSS-level `var(--x, fallback)` does not help here: the
property *is* set, just to a broken token.

The mirror image of this bites just as often: changing a `default` in the schema
does nothing to a section that is already on a page. The saved value wins, so a
setting the merchant never touched keeps whatever it was first saved with, and a
new default only reaches new instances. Re-pasting the file does not clear it
either — the value lives on the page, not in the code.

When a default has to change for an instance that already exists, give the
setting a new `id`. There is no saved value under the new key, so the default
applies on the next render with nothing to change in the editor. The variant
grid's `mobile_columns` became `mobile_grid` for exactly this reason.

Where the same setting drives layout, prefer emitting a class over a CSS
variable: `hp-vg--m2` on the section element says which rule is in force and can
be read straight off the DOM, whereas `repeat(var(--hp-mobile-cols), ...)` looks
the same whatever value it got.

## Brand tokens

From the Totterful brand sheet.

| Role | Value |
| --- | --- |
| Sage | `#808567` brand, `#E9F5DB` / `#CFE1B9` / `#B5C99A` tints |
| Terracotta | `#D88B6D` accent, `#ECA883` peach |
| Cream | `#FCFBF6` |
| Ink | `#2F3326`, `#5C6150` muted |
| Type | Alata headings (one weight, 400), Quicksand body |
| Shape | 24px card radius, pill buttons, 4px spacing base |
