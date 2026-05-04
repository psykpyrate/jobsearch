# Job Scanner Web

This folder contains an HTML/CSS/JavaScript version of the job scanner UI.

What it includes right now:

- Theme picker with 6 themes
- Text size controls
- Compact / Comfortable density
- Filter form
- Job board toggles
- Visible column toggles
- Results table
- Detail pane
- LocalStorage-backed saved settings
- Optional test sound button using `../95.mp3`

What it does not include yet:

- Live scraping/search from job boards
- Python backend integration
- Browser-safe notification pipeline

## Open it

You can open `index.html` directly in a browser, but for the smoothest behavior use a small local server.

Example with Python:

```powershell
cd "C:\LT_Pybuilds\job scanner\html-app"
python -m http.server 8080
```

Then open:

- `http://localhost:8080`

## Next step

If you want this HTML version to use real live results, the clean path is:

1. Keep this UI as the frontend
2. Add a small backend API that reuses the Python scanner logic
3. Fetch results from the browser app
