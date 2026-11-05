# Daily refresh

This site is updated each morning by the Daily Deals Brief scheduled task, right after it sends the email. It is a **public** website.

## Steps

1. Take the digest you just produced for the email.
2. Write it to `data/briefs/YYYY-MM-DD.json` (today's Adelaide date). If that file exists, overwrite it. Follow the schema below; look at the newest existing file for an example.
3. Run `python3 scripts/build.py`. It regenerates `index.html`, `archive/` and `feed.json`, and deletes briefs older than 30 days.
4. Commit everything (`git add -A`) with the message `Deals for <display date>` and push to `main`. GitHub Pages publishes from `main`.

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
  "categories": [ { "name": "Lawn mowers", "deals": [ DEAL ], "notes": [ "short bullet" ] } ],
  "notes": [ { "label": "Missed", "text": "..." } ],
  "nothing_today": [ "Air fryers", "Rugs" ],
  "sales": [ { "text": "...", "links": [ { "label": "OzBargain", "url": "https://..." } ] } ]
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
  "status": "new | still on | price dropped – was $X yesterday",
  "stretch": false,
  "why": "Why it's good, caveats.",
  "ends": "15 Nov",
  "links": [ { "label": "Retailer", "url": "https://..." } ]
}
```

`category` is only needed for top deals. Empty strings are fine for unknown fields. If nothing meets the bar, use `"top": []` and say so in `summary`.
