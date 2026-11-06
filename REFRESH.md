# Daily refresh

This site is updated each morning by the "Taytino Black Friday Feed" scheduled task, right after it sends the email. It is a **public** website.

## Steps

1. Take the digest you just produced for the email.
2. Write it to `data/briefs/YYYY-MM-DD.json` (today's Adelaide date). If that file exists, overwrite it. Follow the schema below; look at the newest existing file for an example.
3. Run `python3 scripts/build.py`. It regenerates `index.html`, `archive/` and `feed.json`, and deletes briefs older than 30 days.
4. Commit everything (`git add -A`) with the message `Deals for <display date>` and push to `main`. GitHub Pages publishes from `main`.

## Page layout

One scrolling page, top to bottom:
- **Header** with the date, `summary` as the headline, and counts (deals, categories, verified, sales) worked out by the build.
- **Pinned section menu** linking to each section and to every category that has deals.
- **Today's top 5** (`top`, max 5). Only deals with `"verified": "verified"` belong here.
- **What's on**: sales live now or in the next 7 days, from `sales`. Keep `title` short (2–4 words). Give real ISO dates (`YYYY-MM-DD`) for `starts`/`ends` when known, `""` when not; the build works out "3 days left" etc. Set `"confirmed": false` for rumours.
- **Best stores right now**: up to 5 retailers, ranked (`stores`: `name`, `why`, `links`).
- **All deals by category**, with search, "Verified only" and sort controls. Each category with deals shows its `advice` ("buy now or wait") and up to 3 deals (`categories`). A top-5 deal is **also** listed under its own category. Categories with no deals are collapsed into one "Nothing worth buying today" line; their `advice` or `notes` show there, so use `notes` for a best price to watch.
- **Not as good as they look**: from `avoid`, notable fake or inflated discounts (`item`, `retailer`, `why`).
- Each deal card shows price, usual price, saving, badges (verified/unverified, new, price drop, listed since, stretch pick), retailer, end date, reviews, `why`, a fold-out "Price check & delivery" panel, and a button to the first link (the label is generated as "View at <retailer>").
- **Price check**: every deal carries `verified` (`"verified"` or `"unverified"`; leave "not a deal" items out and list notable ones under `avoid`), `lowest` (lowest price on record, with date if known), `price_source` (where the history came from), `reviews` (rating, review count, main complaint) and `delivery` (Adelaide delivery cost/time or click & collect; no street, suburb or postcode).
- **Thumbnails**: set `image` on every deal to the product's photo URL, taken from the product or deal page you already fetched: the `og:image` meta tag, or the main product photo. It must be an absolute `https://` URL to the image itself, copied from the page, never guessed. If you can't find one, use `""`; the page then shows a category icon, and it also falls back to the icon if the image fails to load.
- **Previously posted**: set `previously_posted` on any deal that appeared in an earlier brief, using the display date it was **first** posted (for example `"Sat 31 Oct 2026"`). Use `status` for what changed: `"price unchanged"`, `"price dropped – was $X"`, or `"new"`. The build also labels exact item-name repeats from the archive if you miss one.

## Category names (use exactly; this is the tab order)

BBQs · Coffee machines · TVs · Office screens · Office chairs · Robotic pool cleaners · Large rugs · Air fryers · Microwaves · Slow cookers · Kitchenware · Cordless stick vacuums · Robot vacuums · Lawn mowers · Heat pump dryers · Kettle and toaster packs · Outdoor dining settings

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
  "top": [ DEAL, DEAL, DEAL, DEAL, DEAL ],
  "stores": [
    { "name": "JB Hi-Fi", "why": "Broad real discounts on TVs and monitors; free click & collect.", "links": [ { "label": "Sale", "url": "https://..." } ] }
  ],
  "avoid": [ { "item": "Product", "retailer": "Store", "why": "'Was' price never charged; same price as September." } ],
  "categories": [
    {
      "name": "Coffee machines",
      "advice": "Buy now: at its lowest on record.",
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
  "lowest": "$949 (Jul 2026)",
  "price_source": "PriceHipster",
  "verified": "verified | unverified",
  "reviews": "4.6/5 from 1,200 reviews; some note a noisy fan",
  "delivery": "Free Adelaide metro delivery, 3–5 days; or click & collect",
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
