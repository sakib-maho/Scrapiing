# Input Parameters Guide - What to Provide for What

This guide explains what input parameters you should provide for different scraping scenarios.

## 📋 Available Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `category_url` | string | No | `s-farming-veterinary/nsw/c21210l3008839` | Gumtree category to scrape |
| `max_pages` | number | No | `1` | Maximum number of pages to scrape |
| `max_listings` | number/null | No | `24` (if 1 page) or `null` (if >1 page) | Maximum listings to scrape |
| `location` | string | No | `""` | Location filter (optional) |
| `save_to_sheets` | boolean | No | `true` | Whether to save to Google Sheets |

---

## 🎯 Common Scenarios

### Scenario 1: Scrape 1 Page (Default - 24 Listings)

**Use case:** Quick scrape of first page, limited to 24 listings

**Input:**
```json
{
  "max_pages": 1
}
```

**Or simply:**
```json
{}
```

**What happens:**
- Scrapes page 1 only
- Stops at 24 listings (default limit)
- Saves to Google Sheets (if configured)

---

### Scenario 2: Scrape Multiple Pages (All Listings)

**Use case:** Get all listings from 2, 3, or more pages

**Input:**
```json
{
  "max_pages": 2
}
```

**What happens:**
- Automatically sets `max_listings` to `null` (no limit)
- Scrapes page 1 → gets all listings
- Scrapes page 2 → gets all listings
- Continues until all pages are scraped
- Example: If page 1 has 24 listings and page 2 has 24 listings, you get 48 total

**For 3 pages:**
```json
{
  "max_pages": 3
}
```

**For 5 pages:**
```json
{
  "max_pages": 5
}
```

---

### Scenario 3: Scrape Multiple Pages with Limit

**Use case:** Scrape 2 pages but stop at 50 listings

**Input:**
```json
{
  "max_pages": 2,
  "max_listings": 50
}
```

**What happens:**
- Scrapes page 1 → gets listings (e.g., 24)
- Scrapes page 2 → gets more listings
- Stops when total reaches 50 listings (or finishes page 2)

---

### Scenario 4: Scrape Specific Category

**Use case:** Scrape a different category (e.g., hospitality-tourism)

**Input:**
```json
{
  "category_url": "s-hospitality-tourism/sydney/c18342l3003435",
  "max_pages": 2
}
```

**Common category formats:**
- `s-hospitality-tourism/sydney/c18342l3003435`
- `s-farming-veterinary/nsw/c21210l3008839`
- `s-cars-vans-utes/nsw/c18320l3008839`

---

### Scenario 5: Scrape with Location Filter

**Use case:** Filter listings by location

**Input:**
```json
{
  "max_pages": 2,
  "location": "Sydney"
}
```

**What happens:**
- Scrapes 2 pages
- Only shows listings in "Sydney"
- Location is added as query parameter: `?location=Sydney`

---

### Scenario 6: Scrape but Don't Save to Google Sheets

**Use case:** Test scraping or just get JSON response

**Input:**
```json
{
  "max_pages": 2,
  "save_to_sheets": false
}
```

**What happens:**
- Scrapes 2 pages
- Returns JSON response with all listings
- Does NOT save to Google Sheets
- Useful for testing or API-only usage

---

### Scenario 7: Scrape All Listings Explicitly

**Use case:** Explicitly set no limit (same as Scenario 2)

**Input:**
```json
{
  "max_pages": 2,
  "max_listings": null
}
```

**What happens:**
- Same as Scenario 2
- Explicitly tells scraper: "no limit"
- Scrapes all listings from 2 pages

---

## 📝 Examples for n8n Workflow

### Example 1: Quick Test (1 page, 5 listings)
```json
{
  "max_pages": 1,
  "max_listings": 5,
  "save_to_sheets": false
}
```

### Example 2: Production Scrape (2 pages, all listings)
```json
{
  "category_url": "s-farming-veterinary/nsw/c21210l3008839",
  "max_pages": 2,
  "save_to_sheets": true
}
```

### Example 3: Large Scrape (5 pages, all listings)
```json
{
  "max_pages": 5,
  "save_to_sheets": true
}
```

### Example 4: Limited Scrape (3 pages, max 100 listings)
```json
{
  "max_pages": 3,
  "max_listings": 100,
  "save_to_sheets": true
}
```

---

## 🔄 How Parameters Interact

### `max_pages` and `max_listings` Logic:

| max_pages | max_listings | Result |
|-----------|--------------|--------|
| `1` | Not provided | Scrapes 1 page, stops at 24 listings |
| `2` | Not provided | Scrapes 2 pages, gets ALL listings (auto `null`) |
| `2` | `null` | Scrapes 2 pages, gets ALL listings |
| `2` | `50` | Scrapes up to 2 pages, stops at 50 listings |
| `5` | Not provided | Scrapes 5 pages, gets ALL listings (auto `null`) |
| `5` | `100` | Scrapes up to 5 pages, stops at 100 listings |

**Key Rule:** If `max_pages > 1` and `max_listings` is not provided, it automatically becomes `null` (no limit).

---

## 🎯 Quick Decision Tree

**Q: How many pages do you want?**
- **1 page** → Just set `max_pages: 1` (or leave default)
- **Multiple pages** → Set `max_pages: 2` (or more)

**Q: Do you want all listings or a limit?**
- **All listings** → Don't set `max_listings` (auto `null` when `max_pages > 1`)
- **Specific limit** → Set `max_listings: 50` (or your number)

**Q: Which category?**
- **Default category** → Don't set `category_url`
- **Different category** → Set `category_url: "s-category/location/c12345l67890"`

**Q: Need location filter?**
- **No filter** → Don't set `location` (or set to `""`)
- **Filter by location** → Set `location: "Sydney"`

**Q: Save to Google Sheets?**
- **Yes** → Don't set `save_to_sheets` (defaults to `true`)
- **No** → Set `save_to_sheets: false`

---

## 📊 Real-World Examples

### Example A: Daily Scrape of Farming Jobs (2 pages)
```json
{
  "category_url": "s-farming-veterinary/nsw/c21210l3008839",
  "max_pages": 2
}
```
**Result:** Gets all farming jobs from first 2 pages, saves to Google Sheets

### Example B: Quick Test of Hospitality Category
```json
{
  "category_url": "s-hospitality-tourism/sydney/c18342l3003435",
  "max_pages": 1,
  "max_listings": 5,
  "save_to_sheets": false
}
```
**Result:** Quick test, gets 5 listings, doesn't save to sheets

### Example C: Large Scrape for Analysis (5 pages, no sheets)
```json
{
  "max_pages": 5,
  "save_to_sheets": false
}
```
**Result:** Gets all listings from 5 pages, returns JSON only (for analysis)

### Example D: Limited Scrape with Location
```json
{
  "max_pages": 3,
  "max_listings": 50,
  "location": "Sydney",
  "save_to_sheets": true
}
```
**Result:** Gets up to 50 listings from 3 pages, filtered by Sydney, saves to sheets

---

## ⚠️ Important Notes

1. **`max_listings` priority:** If you set both `max_pages` and `max_listings`, the scraper will stop when it reaches the `max_listings` limit, even if it hasn't finished all pages.

2. **Auto `null` behavior:** When `max_pages > 1` and you don't provide `max_listings`, it automatically becomes `null` (no limit). This is the new behavior.

3. **Single page default:** When `max_pages = 1`, the default `max_listings` is 24.

4. **Location filter:** The location parameter filters results. If a page has no listings matching the location, you might get fewer results.

5. **Google Sheets:** Requires `GOOGLE_CREDENTIALS` and `GOOGLE_TOKEN` to be set in Railway. If not set, set `save_to_sheets: false` to avoid errors.

---

## 🚀 Quick Start Recommendations

**For testing:**
```json
{
  "max_pages": 1,
  "max_listings": 5,
  "save_to_sheets": false
}
```

**For production (2 pages, all listings):**
```json
{
  "max_pages": 2
}
```

**For large scrape (5 pages, all listings):**
```json
{
  "max_pages": 5
}
```

