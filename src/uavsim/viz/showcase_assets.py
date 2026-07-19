"""Fallback static assets for the React showcase (also mirrored under docs/showcase/)."""

# Kept in sync with docs/showcase/* — generator copies docs/ first when present.

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>uavsim · flight results</title>
  <link rel="stylesheet" href="./styles.css" />
  <script crossorigin src="https://unpkg.com/react@18.3.1/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js"></script>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
  <div id="root">
    <p class="loading">Loading showcase…</p>
  </div>
  <script src="./app.js"></script>
</body>
</html>
"""

# Prefer docs/showcase/styles.css and app.js; these are install-fallback only.
STYLES_CSS = "body { font-family: system-ui, sans-serif; margin: 1rem; }\n"
APP_JS = "document.getElementById('root').textContent = 'Missing docs/showcase assets';\n"
