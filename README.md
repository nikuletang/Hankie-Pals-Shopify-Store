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
| [`sections/problem-cards.liquid`](sections/problem-cards.liquid) | **Problem blobs** | Eyebrow pill, display heading, three organic blob cards that pop, wobble or squish in as the section arrives |
| [`sections/pals-picker.liquid`](sections/pals-picker.liquid) | **Meet the Pals** | Character picker: choosing a Pal swaps the photo, tint, copy and buy button |
| [`sections/solution-tabs.liquid`](sections/solution-tabs.liquid) | **Solution tabs** | Three feature cards; picking one crossfades the large image beside them |
| [`sections/hero-split.liquid`](sections/hero-split.liquid) | **Split hero** | Two panels with independent backgrounds: copy and an offset CTA left, a portrait right. Stays side by side on a phone unless set to stack |
| [`sections/variant-grid.liquid`](sections/variant-grid.liquid) | **Variant grid** | Full-width cards, one per variant of a single product, with a hover image swap |
| [`sections/why-choose.liquid`](sections/why-choose.liquid) | **Why choose us** | A heading over a row of value props, each with an icon drawn in SVG rather than uploaded |
| [`sections/why-pills.liquid`](sections/why-pills.liquid) | **Why choose — pills** | The same headline, with each reason as a big colourful pill that falls into place. An alternative to the icon version, not a replacement |
| [`sections/section-divider.liquid`](sections/section-divider.liquid) | **Section divider** | A shaped edge — torn, zigzag, wave, scallop, slant, arch — to sit between two sections |
| [`sections/marquee.liquid`](sections/marquee.liquid) | **Scrolling marquee** | A band of text and images sliding past, with filled or outlined lettering |
| [`sections/pal-reveal.liquid`](sections/pal-reveal.liquid) | **Pal reveal** | A Pal that grows on scroll until its body becomes the next section |
| [`sections/pal-panel.liquid`](sections/pal-panel.liquid) | **Pal panel** | A domed Pal-shaped panel that rises over the pinned section above and holds the copy |
| [`sections/hp-header.liquid`](sections/hp-header.liquid) | **Totterful header** | Logo, the site's buttons as navigation, search, account and cart. Transparent over the hero. Goes in the header section group |
| [`sections/how-to-steps.liquid`](sections/how-to-steps.liquid) | **How-to steps** | Numbered capsule rows: a round tinted photo, a title, a line of copy, and a very pale numeral behind the words |
| [`sections/feature-collage.liquid`](sections/feature-collage.liquid) | **Feature collage** | Overlapping photographs in the middle with pills placed on them by hand, feature cards either side. Hovering a photo lifts it over the rest |
| [`sections/hp-pal-buy.liquid`](sections/hp-pal-buy.liquid) | **Choose your Pal** | The product page's picking moment. One pill per Pal; choosing one swaps the photo, the name, the blurb and the accent, and selects that variant in Dawn's own buy box below |
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

## A reveal that takes itself away

The tabs in **Solution tabs** slide in from the right, staggered. What makes
this one different from the other reveals is that the element already owns its
`transform`: the hover lift is `.hp-sol__tab:hover`, and a reveal rule scoped
under the section class outranks it. Left in place, the reveal would kill the
hover for the rest of the page's life — not at the moment it is written, but
quietly, the first time someone moves a mouse over a tab.

So the reveal is a transition rather than keyframes, and the class that carries
it comes off as soon as the last tab lands. The section afterwards is exactly
what it was before: no `is-in`, no inline delays, no reveal class.
`scripts/test-solution-tabs.py` asserts that by comparing the settled
`transition-property` against the same section rendered with motion set to
None, which is the closest thing to "prove nothing is left behind".

The reveal lives in its own `<hp-sol-reveal>`, not in the `<hp-solution-tabs>`
element beside it. The tab behaviour — roles, keyboard, selection — is already
written and a reveal has no business anywhere near it. The element draws
nothing (`display: none`), finds the tabs itself, and observes the list they sit
in rather than itself, since a `display: none` element never intersects
anything. The suite checks the tablist is still a tablist of buttons and the
first tab is still selected, because breaking that is the cost of getting this
wrong.

    python3 scripts/test-solution-tabs.py

Seventeen cases: the start state and its direction on each of the four motions,
the stagger, the landing, the class removing itself, the distance setting, the
roles and selection surviving, and the three bail-outs.

## Falling into place without a physics engine

The pills in **Why choose — pills** land packed against each other, one after
the next. They are not simulated. A real engine settles differently on every
screen width and every reload, adds a dependency, and cannot be checked — so
the arrangement is laid out deliberately, alternating sides with a set tilt,
and each pill is animated falling into the place it already has. Same feeling,
same result for every visitor, and the claim is testable.

Which matters, because the claim is geometric and the layout box cannot answer
it: the tilt is a `transform`, so it is not in the box. Each pill is a capsule
— `border-radius: 999px` on a box of height H is a rectangle with semicircular
ends of radius H/2, which is a line segment thickened by H/2 — and two capsules
intersect exactly when the distance between their segments is less than the sum
of their radii. `scripts/test-why-pills.py` measures that for every pair at five
widths.

Two things that fell out of measuring rather than looking:

- **The usual segment-distance formula is wrong here.** Clamping its two
  parameters independently overestimates whenever the unclamped solution lands
  outside the segments; it put two pills 109px apart that a drawing put 41px
  apart, which quietly hid an overlap. Either the segments cross, or the closest
  point is one of the four endpoints against the other segment.
- **A tilted pill reaches past its own row**, by about `w·sin(θ)/2`, and the
  pills get wider relative to the page as the page narrows — so a gap that looks
  generous at 1600px overlaps at 750px. The gap has a floor that rises with the
  tilt, and the defaults (3deg, 26px, 150px inset) were picked by sweeping both
  and reading the closest approach at each width: 23px at 1600, 3px at 750,
  never below zero.

### Three ways a headless browser lies about animation

All of these cost a wrong answer before they were pinned down, and both reveal
suites are built around them:

- **Animation timelines do not advance under `--virtual-time-budget`.** An
  animation sits on its first frame however long the budget is, and a `finished`
  promise never settles. Waiting for one hangs the run.
- **Shortening it to `animation-duration: 0s` does not settle it either.** With
  no animation frames the animation never starts, so its fill never applies.
  Removing the animation is what settles it, and asks the same question: every
  last keyframe here is `opacity: 1; transform: none`, so what the cascade
  resolves to with no animation is where the animation lands.
- **IntersectionObserver delivery needs "update the rendering"**, a step a page
  with nothing to draw never schedules — so the observer may simply never fire,
  and every assertion downstream reads as a broken animation rather than a flaky
  harness. Three nudges together fixed it: forcing layout on each poll, asking
  for a frame (`requestAnimationFrame` never *fires* under a virtual budget, so
  it is raced against a timer rather than waited on), and putting an endless
  1px animation on `body::after` to keep the rendering loop turning while the
  observer is being waited for.

To *see* a frame rather than measure one, a negative `animation-delay` with
`animation-play-state: paused` holds an animation at that point in its run,
which works even with the clock frozen.

    python3 scripts/test-why-pills.py

Thirty-eight cases: the arrangement and its alternating sides and tilt, no pair of
pills overlapping at five widths or at the tightest settings the editor allows,
nothing off the edge, the size control, the per-pill tilt override, the picture
appearing only when both the toggle and an image are set and sitting centred
between the headline and the pills, the stagger, each of the four motions, the
tilt surviving the landing, contrast on every pill in the preset, and the three
bail-outs, the shadow, and the outline.

The outline is a spread-only `box-shadow` rather than a `border`, and that is
not a style preference: a border is in the box, so 5px of it would add 10px to
every pill's height and eat the clearance the stack is tuned to. A spread-only
shadow is painted outside the box, follows the `border-radius` exactly, and
changes no geometry — the suite asserts every pill is the same size with the
outline on and off. It is listed before the soft shadow so it paints over it,
and the gap between pills opens by twice its width, because two neighbours each
grow towards each other by it.

Both live in the one `box-shadow`, which is also why the suite cannot split the
computed value on commas: the colours inside it have commas of their own. Each
layer begins with its colour, and that is what the parser anchors on.

## Animating something that is not a rectangle

The blobs arrive on keyframes rather than a transition, because every entrance
worth having overshoots and a transition only goes from one value to another.
The wobble is the one with a trick in it: it sets `border-radius` at 0% and 40%
and **leaves it out of the last frame**, so the browser builds the missing 100%
from the underlying rule and each blob morphs back to whichever of the three
lopsided shapes its `nth-child` gave it. Add a fourth shape up in the CSS and
the animation needs no change at all.

That is also the thing that would fail silently — every blob ending up the same
shape looks deliberate — so `scripts/test-blob-reveal.py` checks both halves of
it: that the last keyframe declares no radius, read out of the CSSOM, and that
the three blobs still hold three distinct shapes once settled.

### Three ways a headless browser lies about animation

All of these cost a wrong answer here before they were pinned down:

- **Animation timelines do not advance under `--virtual-time-budget`.** An
  animation sits on its first frame however long the budget is, and a `finished`
  promise never settles. Waiting for one hangs the run.
- **Shortening it to `animation-duration: 0s` does not settle it either.** With
  no animation frames the animation never starts, so its fill never applies and
  the element stays at the hidden underlying value. Taking the animation away
  entirely is what settles it — every last keyframe here is `opacity: 1;
  transform: none`, so what the cascade resolves to with no animation is where
  the animation lands.
- **IntersectionObserver delivery is lifecycle-dependent**, and on a page with
  nothing to do the lifecycle may never run: about one run in five it never
  fired, and every assertion downstream read as a broken animation rather than
  a flaky harness. Reading a layout property (`document.body.offsetHeight`) on
  each poll forces the style and layout pass it needs. The checks that are about
  the animation call `play()` on the element directly, and whether the observer
  fires at all is one check of its own.

To *see* a frame rather than measure one, a negative `animation-delay` with
`animation-play-state: paused` holds the animation at that point in its run,
which works even with the clock frozen.

    python3 scripts/test-blob-reveal.py

Nineteen cases: the observer firing, the stagger and its tidying-up, each of the
five styles, the wobble's shapes, and the four ways it can bail — none, reduced
motion, no IntersectionObserver, and the theme editor tearing the section out
and putting it back.

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

## Installing the header

Same mechanism as the footer, and the same one line in the schema —
`"enabled_on": { "groups": ["header"] }` — so it can only be added where it
renders on every page.

1. **⋯ → Edit code** → **Sections → Add a new section**, name it `hp-header`,
   paste the file, **Save**.
2. **Customize**, scroll to the **Header** area, **Add section**, pick
   *Totterful header*, and drag it under the announcement bar.
3. Hide Dawn's own header with the eye icon rather than deleting it.
4. Optionally pick a menu under **Links**. With nothing picked the store's own
   `main-menu` is used, so the bar is never empty just because a setting was
   not filled in. Three or four entries is the limit before the bar crowds the
   logo.

A schema `default` does not cover that fallback and it is worth knowing why:
Shopify bakes defaults in when a section instance is first saved, so a section
already on the page keeps the empty value it was saved with no matter what the
schema says later. The fallback has to happen in Liquid, at render time.

The guard counts links rather than testing the menu against `blank`. A menu
that is not there is `nil` in one Liquid and an `EmptyDrop` in another and the
two do not agree about `!= blank`; nothing disagrees about how many links it
has. `nil > 0` is false in Shopify but *raises* in python-liquid, so the count
goes through the `size` filter, which answers 0 for nil, for an empty string
and for a menu with no links.

The menu's wording lives in the Shopify admin under **Content → Menus**, not in
this section. Renaming or deleting an entry there changes the bar; there is
nothing to edit here.

**Where it folds into a hamburger is a setting**, not a fixed 990px. Long link
names crowd the bar sooner than short ones, so it is worth tuning. Two things
about it are easy to misread:

- **Phone widths are measured in an iframe.** Headless Chromium will not open
  a window under 500px, and at 500px all of this fitted — which is exactly how
  a 390px overflow shipped. `framed()` puts the page in an iframe of the true
  width, where `innerWidth` really is 390.
- **The Customize preview is much narrower than the real site.** The editor
  sidebar takes 300-400px, so a preview on a laptop can be under 900px and show
  the hamburger while the live site shows the buttons. Judge it on the live
  site, not in the editor.
- **Every rule here that competes with `.hp-btn` carries `.hp-nav` as well.**
  A single class weighs the same as `.hp-btn`, so which one won was decided by
  which stylesheet loaded first — and since `hp-button.css` is installed by
  hand into `theme.liquid`, that order is not this file's to promise. It cost
  two bugs before the pattern was applied properly. The second was the worse
  one: `.hp-nav__icon` sets `--hp-btn-pad-x: 12px`, `.hp-btn` sets `32px`, and
  when the shared file landed last every icon pill grew from 44px to 68px. On a
  390px phone that put the hamburger at x=392 — off the edge, untappable, and
  dragging the whole page sideways when you tried. The suite now loads
  `hp-button.css` *last* for its layout measurements, which is the state a real
  store is in.

The bar is three grid columns — logo, links, icons — rather than a flex row.
The middle column is then centred on the bar itself instead of on whatever room
is left beside the logo, so changing the logo width does not shift the links.
The columns are assigned explicitly because the middle one is not rendered at
all when there is no menu, and the icons would otherwise slide into its place.

On a phone the bar carries the logo, account, cart and hamburger. Search stands
down, because a fifth pill does not fit 390px and a bar that overflows drags the
whole page sideways. **Keep search on a phone** puts it back.

The bar is transparent and stays transparent as the page scrolls, which only
works because every pill carries its own fill, outline and shadow. The logo is
on a pill for the same reason and should stay there: a bare wordmark disappears
over the sage panel and over a photograph.

### Where it meets Dawn

This is the only section that has to interoperate with the theme rather than
sit beside it, so the surface is kept deliberately small:

- **The cart** is the one real dependency. A hidden `#cart-icon-bubble` sits in
  the header; Dawn writes the live count into that id after every add to cart,
  and a `MutationObserver` copies the number into the visible bubble. It reads
  the element Dawn marks as the visible one rather than the whole text, because
  Dawn prints the count twice — once for eyes, once for a screen reader, with
  nothing between them, so "4" and "4 items" read as **44**.
- **That observer writes to the DOM**, which is how an observer feeds itself.
  It ran away in testing and hung the browser outright: not a slow page, a page
  that never finished. It now writes only when the count has changed and
  disconnects while it does.
- **The drawer** opens through `<cart-drawer>` when there is one and follows the
  link to the cart page when there is not, so the cart works with the drawer
  off, with the script failed, and with JavaScript disabled.
- **Nothing else** touches Dawn. Search is a form posting to `/search`, the
  account icon is a link, and the mobile menu is ours.

Two CSS traps this section ran into, both worth remembering:

- **`hidden` is a UA rule, and a UA rule loses to any author rule.** The burger
  showed the hamburger and the cross at the same time, because
  `.hp-nav__icon svg { display: block }` outranked it. It needs an explicit
  `svg[hidden] { display: none }`.
- **The shared button stylesheet is loaded *before* this section's own rules**,
  the opposite of every other section. The shared file owns what a button looks
  like; this file owns where one goes, and `display: none` on the burger has to
  beat `.hp-btn`'s own display at the same weight.

    python3 scripts/test-header.py

Thirty-one cases. Dawn is not here to test against, so the two places they meet
are simulated narrowly and honestly: the page rewrites `#cart-icon-bubble` the
way Dawn does and the suite asserts the bubble follows, and a stand-in
`<cart-drawer>` asserts the button opens it rather than navigating. Neither
proves Dawn's behaviour — they prove this header keeps its side of the bargain,
which is the half that can be got wrong here.

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

## Choose your Pal, and the line it does not cross

`hp-pal-buy.liquid` is the product page's picker. It deliberately **does not
take the money**: Dawn's buy box stays below it and keeps the price, the stock
count, the sold-out state and Add to cart. This section only decides which
variant Dawn has selected.

It reaches Dawn three ways, in order of how much of Dawn keeps working:

1. a radio input whose value is the option — Dawn's "pill" picker
2. a `<select>` carrying that option — Dawn's dropdown picker
3. the product form's hidden `input[name="id"]`, so at least the right variant
   is added even when neither picker is found

If none of them is on the page the click is left alone and the browser follows
the pill's `href` to `?variant=<id>`, which selects it on the way in. So the
picker survives the script failing and JavaScript being off — the same bargain
the header's cart button makes. `scripts/test-pal-buy.py` stands all three
shapes up as stand-ins and asserts each one is driven; neutering the code turns
five checks red, and the fall-through still lands on the right variant.

**Install it above Dawn's product section**, not instead of it. *Hide the
theme's own variant picker* is on by default so there is only one control on
screen; it hides the duplicate dropdown and nothing else.

### richtext cannot go in a `<p>`

A `richtext` setting emits its own `<p>`. Put that inside a `<p>` of your own
and the parser closes yours early — the words end up outside the styled element
and fall back to the theme's size, which under Dawn's 62.5% root renders 17px
as **10px**. It is visible in a screenshot long before it is obvious in the
code. richtext goes in a `<div>`, and the check measures the element the text
actually landed in rather than the one it was meant to land in.

## Placing a pill by hand

In **Feature collage**, a pill's position is a percentage of *the photograph it
belongs to*, not of the collage. That is the whole point: set a pill beside an
ear and it stays beside that ear at every screen width, because both the photo
and the pill are placed in the same percentage space and the stage just gets
narrower.

Two things make that work:

- **The tilt is on the picture, not on the box.** `.hp-fc__photo` stays square
  to the page and holds the position; `.hp-fc__shot` inside it carries the
  rotation. Rotate the box and every pill on it tilts too.
- **Hovering lifts by `z-index`, never by reflow.** Nothing moves, so no pill
  can change place when a photo comes forward. A check asserts every photo is
  in the same position before and after.

### Depth, and the icon beside the words

The photographs carry a real drop shadow — large blur, negative spread, a
genuine vertical offset — set on the picture itself so it follows the rounded
corners instead of boxing them. **Photo depth** drives it, and at 0% the
declaration is not emitted at all, so off is off rather than a transparent
shadow.

Each card is a row: the icon sits in a tile beside the subheading and
paragraph, not above them. The cards on the right are the mirror — tile to the
outside, words reading inward — and on a phone that mirroring is dropped, since
nothing is to either side of anything any more and half the cards would
otherwise read backwards.

**Card style** switches between the boxed version and one with no box at all,
just a hairline between cards, which lets the photographs carry the section.

### A photograph can hang out of the stage

A photo is *placed* by percentage but *sized* by its own height, so a tall one
can reach past the bottom of the collage and land on the card beneath it. The
preset is set so that square photographs stay inside; a much taller one needs
its **Down** lowered by hand. Two checks hold the shipped settings — one
against the stage, one against the first card on a phone.

### A pill near an edge anchors to its own edge

A pill centred on its anchor point spills outward, and a pill hanging off the
page drags the whole page sideways. So the anchor moves: below 28% the pill
grows rightwards from its point, above 72% it grows leftwards, and in between
it stays centred. `overflow-x: clip` on the section is the guarantee behind
that rather than the plan — `clip` and not `hidden`, because `hidden` on one
axis forces the other to scroll and would trap the hover lift.

This was found in a screenshot at 390px, with "Crinkle ears" cut off by the
left edge. The suite measures every pill's box against the viewport at five
widths plus a real 390px phone in an iframe; removing the anchoring turns that
check red and names the pill.

## Sideways scroll on a phone

`scripts/check-overflow.py` renders every section on its own at 390px and
360px and names any element that reaches past the edge. Run it alongside
`check-schemas.py`.

It exists because this has now shipped three times:

- **the header** — its icon pills grew from 44px to 68px when `hp-button.css`
  loaded after the section, pushing the hamburger to x=392 on a 390px phone;
- **the feature collage** — pills anchored by their middles hung off the screen
  when their anchor sat near an edge;
- **the solution tabs** — they slide in *from the right*, so for the length of
  the animation they stand outside the section. At rest nothing is wrong, which
  is why it went unnoticed.

The lesson each time: **horizontal overflow is a property of the document, not
of the section that causes it.** Empty space beside the header when you drag
the page sideways says nothing about the header — the culprit was a section
several screens below. Scan everything rather than reading the symptom's
location as evidence.

### The harness has to share Dawn's box model

The first run of that scan reported two overflowing sections. One was real. The
other was an artifact: `render-section.py` did not set
`box-sizing: border-box`, Dawn does, and `width: 100%` plus padding overflows
under `content-box` and nowhere else. A test page that differs from the store
invents bugs as readily as it hides them, and a false one costs more than a
missed one — it sends you rewriting code that was correct. The reset now
matches Dawn's.

## The numeral in the how-to steps

It is far larger than the row that holds it, which makes it three problems at
once and each is handled somewhere different:

- **It must not change the row.** It is absolutely positioned and the row is
  `overflow: hidden`, so it is clipped against the capsule's rounded end
  instead of stretching the row or reaching outside it. Remove the clip and
  the check names the numeral's right edge against the row's.
- **It must sit behind the words.** The numeral is `z-index: 0`, the photo and
  the words are `z-index: 1`. The text block is `flex: 1`, so a long line runs
  on over the numeral rather than stopping short of it — which is what the
  reference does, and the reason the ordering matters at all. The suite checks
  the ordering with copy long enough to actually cross it; with short copy the
  two never meet and the check would prove nothing.
- **It must not be read aloud.** The list is an `<ol>`, so the order is in the
  markup already. The numeral is `aria-hidden`, or a screen reader announces
  every step twice — "one" from the list, "01" from the decoration.

Where the words cross the numeral the contrast is **5.39:1** against the quiet
text colour, so the overlap stays readable rather than merely faint.

## A range default has to land on a slider stop

Shopify rejects a section whose range `default` sits between two stops — not
the one setting, the whole file, at paste time:

> Invalid schema: setting with id="tighten_below" default must be a step in
> the range

`min: 500, step: 10` makes the stops 500, 510, 520 … and 749 is not one of
them. 749 is the conventional CSS breakpoint, which is exactly why it got
typed; the slider cannot reach it.

`check-schemas.py` already required the *max* to be reachable from the min,
and the default to be *inside* the range. It did not require the default to be
reachable, which is a different rule and the one Shopify actually enforced. It
does now, and it names the nearest valid stop. Run it over all sixteen
sections and this was the only one.

The wider caution: that script is a reimplementation of Shopify's validator
from the outside, so it is only as complete as the rules that have bitten so
far. A clean run means nothing known is wrong, not that Shopify will accept
the file.
