# Working on this store with Claude

## Always link the code on GitHub

Every time a section is changed and pushed, end the reply with GitHub links —
without being asked:

- the file on `main`, e.g.
  `https://github.com/nikuletang/hankie-pals-shopify-store/blob/main/sections/<name>.liquid`
- the same file pinned to the commit just pushed, so the link keeps showing
  that version after `main` moves on
- the commit itself, for the diff alone

Attach the `.liquid` file to the reply as well. The store is not connected to
this repository: nothing reaches the storefront until the file is pasted into
Shopify by hand, so the file and the link are the actual delivery.

## What this repository is

Section files for the Totterful / Hankie Pals storefront
(`totterful-00c6hcep.myshopify.com`, Dawn theme). Each section is pasted into
**Edit code → Sections** and added in **Customize**. The theme itself is not in
this repository, so anything that has to meet Dawn is reasoned about rather
than read.

`README.md` holds the per-section notes and the traps that have already cost
time -- Shopify's, Liquid's and headless Chromium's. Read it before changing a
section, and add to it when a new one bites.
