# Daily refresh

This site is updated each morning by the Daily Deals Brief scheduled task, right after it sends the email. It is a **public** website.

## Steps

1. Take the digest you just produced for the email.
2. Write it to `data/briefs/YYYY-MM-DD.json` (today's Adelaide date). If that file exists, overwrite it. Follow the schema below; look at the newest existing file for an example.
3. Run `python3 scripts/build.py`. It regenerates `index.html`, `archive/` and `feed.json`, and deletes briefs older than 30 days.
4. Commit everything (`git add -A`) with the message `Deals for <display date>` and push to `main`. GitHub Pages publishes from `main`.

## Page layout

- **Sales in the next 7 days**: shown first, as cards with a date tile and a countdown chip ("Ends in 3 days", "In 5 days", "Live now"). The build works out the countdown from `starts`/`ends`, so give real ISO dates (`YYYY-MM-DD`) when known, `""` when not. Set `"confirmed": false` for rumours.
- **Top 3 deals**: the focus of the page (`top`, max 3).
- **One tab per category**: the best deals in each category (`categories`, max 3 deals each). A top-3 deal is **also** listed under its own category tab. Categories with no deals still get a tab that says nothing met the bar; leave them out of the JSON or give them empty `deals`.
- **Thumbnails**: set `image` on every deal to the product's photo URL, taken from the product or deal page you already fetched: the `og:image` meta tag, or the main product photo. It must be an absolute `https://` URL to the image itself, copied from the page, never guessed. If you can't find one, use `""`; the page then shows a category icon, and it also falls back to the icon if the image fails to load.
- **Previously posted**: set `previously_posted` on any deal that appeared in an earlier brief, using the display date it was **first** posted (for example `"Sat 31 Oct 2026"`). Use `status` for what changed: `"price unchanged"`, `"price dropped – was $X"`, or `"new"`. The build also labels exact item-name repeats from the archive if you miss one.

## Category names (use exactly; this is the tab order)

TVs · Air fryers · Coffee machines · Cordless stick vacuums · Robotic pool cleaners · Lawn mowers · Robot vacuums · Heat pump dryers · Slow cookers · Kettle and toaster packs · Large rugs · Outdoor dining settings · Kitchenware

## Privacy rules (public site)

- No names, email addresses, street or suburb, postcode, or other personal details. Say "Adelaide" for location.
- Write neutrally: "fits the criteria", not "fits your criteria"; "just over the 33–40cm target", not "your range".
- Use the real destination URL, not Gmail/Google redirect links (`google.com/url?q=...`).
- Never invent deals, prices or dates. The site must match the email.

## Schema

```json
{
  "date": "2026-11-06",
  "display_date": "Fri 6 Nov 2026",
  "summary": "One or two sentences.",
  "top": [ DEAL, DEAL, DEAL ],
  "categories": [
    {
      "name": "Coffee machines",
      "deals": [ DEAL ],
      "notes_title": "Other Barista Express prices",
      "notes": [ "short bullet", "Missed: ... (sold out)" ]
    }
  ],
  "notes": [ { "label": "Heads up", "text": "anything that fits no category" } ],
  "sales": [
    {
      "title": "IKEA Black Friday",
      "text": "One short sentence: what's on and what it covers.",
      "starts": "2026-11-09",
      "ends": "2026-11-30",
      "confirmed": true,
      "links": [ { "label": "OzBargain", "url": "https://..." } ]
    }
  ]
}
```

DEAL:

```json
{
  "item": "Product name",
  "category": "TVs",
  "retailer": "JB Hi-Fi",
  "price": "$999",
  "usual": "$1,299",
  "saving": "23% off",
  "status": "new | price unchanged | price dropped – was $X",
  "previously_posted": "Sat 31 Oct 2026",
  "stretch": false,
  "why": "Why it's good, caveats.",
  "ends": "15 Nov",
  "image": "https://.../product.jpg",
  "links": [ { "label": "Retailer", "url": "https://..." } ]
}
```

`category` is needed for top deals only. `previously_posted` is `""` for new deals. Empty strings are fine for unknown fields. If nothing meets the bar, use `"top": []` and say so in `summary`.
