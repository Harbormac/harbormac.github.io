# portnaut.com

The website of [Portnaut](https://portnaut.com), the free Mac app for playing Windows games,
made by Built by Argo.

## How it is built

The site is plain HTML and CSS: no framework, no scripts, no tracking, nothing loaded from other
services. GitHub Pages publishes the `docs/` folder of the `main` branch.

- `src/pages/` holds the pages. Each starts with its settings (address, title, description,
  structured data) in a `<!--page {...} -->` comment.
- `src/layout.html` is the frame every page shares (header, footer, search and link-preview tags);
  `src/style.css` the styles.
- `src/build.py` puts the pages in the frame, writes `docs/` with the sitemap and `robots.txt`, and
  checks the result: one main heading per page, unique titles and descriptions, alt text on images,
  internal links that resolve, valid structured data.
- `src/root/` holds files copied to the site's root unchanged: `favicon.ico`, `built-by-argo.png` (the
  logo in the structured data), and `googlefdcfea98ac17e55a.html`, which proves to Google Search
  Console that the site is ours. Keep it.
- `src/make-assets.swift` makes the screenshots, icons and link-preview cards (the site's and one per guide) in
  `src/assets/generated/` from the app's screenshots.

After changing anything in `src/`, run:

```sh
python3 src/build.py
```

and commit both `src/` and `docs/`. The version, download link, Ko-fi link and support address are
set at the top of `src/build.py`; so is the site's address, for moving to a custom domain later.

## Licence

© 2026 Built by Argo. Portnaut is not affiliated with or endorsed by Apple, Valve, Electronic Arts,
Ubisoft, Microsoft, CodeWeavers, Highball or Sikarugir; their names are trademarks of their owners.
