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
