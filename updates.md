# Cyclone Region — Evolutionary Prototype Updates

## 2026-08-30 — Frontend UI/UX, Emergency Help & Helplines

### UI/UX improvements
- Added a red **emergency alert bar** (with tap-to-call `112` and Request Help
  links) to the top of every page: `index.html`, `cyclone_region.html`,
  `history.html`, `about.html`, `report.html`, `helplines.html`.
- Added five **quick-action emergency cards** on the homepage: Request Rescue,
  Medical Help, Find Shelter, Report Damage, Emergency Helplines. They pre-fill
  the help form (`report.html?type=…`).
- Added a **Cyclone Helplines** section on the homepage (112 / 108 / 101 / 1078)
  with tap-to-call `tel:` buttons.
- Reworked the hero on `index.html` with a prominent **Submit Emergency
  Request** action, and polished spacing, buttons, and typography.
- Added lightweight **reveal-on-scroll** animations with `prefers-reduced-motion`
  support.
- Improved mobile behaviour: responsive grids and navigation (hamburger menu)
  for desktop, tablet, and phone widths.
- Added a **footer navigation** with direct links (Home, Live Tracking, History,
  Request Help, Helplines, About) on all pages.

### Emergency help form
- New page `frontend/report.html` — **Report / Request Help** form with: Full
  Name, Mobile, Email (optional), State, District, Village/City, Current
  Location, People Affected, Children, Elderly/Disabled, multi-select Emergency
  Type (Medical, Food, Water, Shelter, Rescue, Missing Person, Other),
  Description, optional image upload (max 2MB), and a required **consent**
  checkbox.
- Prominent **SOS · Submit Emergency Request** button; all required fields are
  validated client-side with clear error messages and ARIA live regions.
- `frontend/assets/helpreport.js` — validates, submits to the backend, previews
  the optional image, and, if the backend is unreachable (e.g. GitHub Pages),
  stores the request in `localStorage` and shows an offline notice so data is
  never silently lost.
- `frontend/assets/emergency.css` — shared styling for the emergency bar, quick
  actions, helpline cards, the help form, keyboard-focus outlines, and
  responsive/reduced-motion rules.

### Backend / API changes
- `backend/app/main.py` — added `POST /api/help-requests` (validated Pydantic
  model; mobile/email/type/image checks; consent enforcement; JSON-lines
  persistence to `backend/data/help_requests.jsonl`) returning a reference id.
- Added `GET /api/help-requests` returning only aggregate counts — personal data
  is never exposed publicly.
- `.gitignore` now excludes `backend/data/` so submitted personal data is never
  committed; `backend/.env.example` documents the optional `HELP_REQUESTS_FILE`.

### Helplines page
- New page `frontend/helplines.html` — clearly labelled national emergency
  numbers (112 Emergency, 108 Ambulance, 101 Fire & Rescue, 1078 Disaster
  Helpline) as tap-to-call cards, plus an extended disaster-response table and a
  disclaimer asking users to verify local/state numbers and follow official
  IMD/NDMA advisories.

### Accessibility improvements
- Proper `<label>` associations, `aria-required`, `role="alert"/status` live
  regions, a skip-to-content link, visible `:focus-visible` outlines, good
  contrast, and a responsive keyboard-navigable form.

### Testing performed
- JavaScript syntax checked with Node for `helpreport.js` and the inline reveal
  script.
- Backend module imported and endpoint logic exercised with a local Python test
  (valid submission writes JSON-lines; invalid payloads are rejected).
- Verified every HTML page opens, the revised nav links resolve to existing
  files, the cyclone prediction (`cyclone_region.html#evolution`), regional
  map, history timeline, about page, and chatbot script remain intact.
- Confirmed the grid layouts collapse correctly for tablet/mobile widths and
  that the GitHub Pages workflow (static `frontend/` deploy) is unaffected.

### Files changed
- `frontend/index.html`, `frontend/history.html`, `frontend/about.html`,
  `frontend/cyclone_region.html`
- `frontend/report.html` (new), `frontend/helplines.html` (new)
- `frontend/assets/emergency.css` (new), `frontend/assets/helpreport.js` (new)
- `backend/app/main.py`, `backend/README.md`, `backend/.env.example`
- `.gitignore`, `README.md`, `updates.md`
## 2026-08-29

### Implemented
- Upgraded `frontend/cyclone_region.html` with an interactive **Cyclone Evolution Timeline**.
- Added predefined observations for:
  - 2008-08-25 00:00
  - 2008-08-25 06:00
  - 2008-08-25 12:00
  - 2008-08-25 18:00
  - 2008-08-26 00:00
  - 2008-08-26 06:00
  - 2008-08-26 12:00
  - 2008-08-26 18:00
  - 2008-08-27 00:00
  - 2008-08-27 06:00
  - 2008-08-27 12:00
- Added selectable timeline with previous/current/next observation context.
- Added `PLAY EVOLUTION`, `PAUSE`, and `RESET` controls.
- Added dynamic current cyclone state cards for storm name, ID, time, location, classification, wind, pressure, movement, distance, and recent changes.
- Added dynamic evolution-stage calculation: formation/depression, tropical storm, rapid intensification, peak intensity, and weakening.
- Added an India / northern Indian Ocean regional demonstration map with:
  - historical track
  - current animated intensity marker
  - deterministic +6h/+12h/+24h/+48h demo prediction track
  - hover tooltips for historical points
  - regional labels and coordinate grid
- Added deterministic demo environmental conditions for:
  - sea-surface temperature
  - atmospheric moisture
  - vertical wind shear
  - pressure trend
  - wind trend
  - upper-level outflow
  - ocean heat content
  - Coriolis support
- Added a prototype **Cyclone Development Favorability Score / 100** with progress bars and explicit heuristic disclaimer.
- Added deterministic demo prediction cards for +6h, +12h, +24h, and +48h.
- Added deterministic **Demo Confidence** indicator based on observation history and trend consistency.
- Added a dynamic **Why This Prediction?** explanation that changes with the selected observation.
- Added lightweight inline SVG wind-speed and central-pressure evolution charts; no new dependency was introduced.
- Preserved the existing header, navigation, region filter, original map, risk profile, methodology section, footer, and chatbot.
- Added responsive styling for desktop, tablet, and mobile layouts.
- Added explicit scientific/product disclaimer:
  - `EVOLUTIONARY PROTOTYPE — DEMO DATA & HEURISTIC PREDICTION`
  - Prototype is not an operational weather forecast.

### Important data note
The supplied feature dataset contains GUSTAV (`AL072008`) in the **Atlantic basin**, so its real longitudes are west of the India-focused 60°E–100°E map. To keep the requested India regional visualization geographically bounded, the prototype retains the supplied GUSTAV wind/pressure/change evolution while using deterministic **regional demonstration coordinates** for the interactive India map. The UI does not claim those regional coordinates are Gustav's real historical track.

### Files changed
- `frontend/cyclone_region.html`
- `updates.md`

### Dependencies
- No new JavaScript package or external weather API was added.
- Existing project structure and navigation were preserved.

### Validation performed
- Confirmed the upgraded HTML file was written successfully.
- Confirmed the prototype data and controls are embedded in the page.
- Confirmed the project archive can be repackaged with the new page and `updates.md`.

## 2026-08-29 — Map & User Input Upgrade

### Implemented from latest UI review
- Reworked the evolutionary map to use a cleaner **geographic India / northern Indian Ocean projection** with a proper 60°E–100°E and 0°N–35°N coordinate frame.
- Replaced the previous oversized/distorted India silhouette with a more proportionally aligned India outline for the requested regional view.
- Added clearer neighbouring geography/context labels for Pakistan, Bangladesh, Myanmar and Sri Lanka, plus Arabian Sea and Bay of Bengal labels.
- Added subtle geographic grid lines and state/region guide lines without overwhelming the cyclone track.
- Kept the historical track, current cyclone marker, forecast track and hover tooltips synchronized with the geographic coordinates.
- Added a **User Controlled Demo Scenario** panel so the values are no longer UI-hardcoded only.
- Added editable inputs for:
  - Storm Name
  - Storm ID
  - Date / Time (UTC)
  - Latitude
  - Longitude
  - Wind Speed
  - Central Pressure
  - Movement Speed
  - Movement Direction
  - Wind Change / 6h
  - Pressure Change / 6h
  - Sea Surface Temperature
  - Atmospheric Moisture
  - Vertical Wind Shear
  - Upper-Level Outflow
  - Ocean Heat Content
- Added `APPLY TO CURRENT` to update the selected observation immediately.
- Added `ADD AS NEW OBSERVATION` to create a new user-defined timeline point and automatically reorder the timeline chronologically.
- Added `RESTORE SAMPLE VALUES` to return to the original GUSTAV demo sequence.
- User-entered values now drive the cyclone state, evolution stage, environmental factor panel, favorability score, demo prediction, prediction explanation, map marker/track and charts.
- Added input validation for the core numeric/time fields.
- Existing sample data, PLAY/PAUSE/RESET controls and navigation remain intact.

### Validation
- JavaScript syntax checked successfully with Node.js.
- Confirmed all new input element IDs are unique.
- Confirmed the evolutionary script initializes the form from the selected observation.
- Confirmed the page remains frontend-only and does not require backend inference or a live weather API.

## 2026-08-29 — Evolution Map & Visual Reference Update
- Added the supplied Cyclone Evolution Timeline visual as `frontend/assets/evolution-timeline-reference.png` and displayed it at the top of the Evolutionary Prototype section.
- Preserved the supplied original screenshot as `frontend/assets/evolution-reference-original.png` for project reference.
- Added `frontend/assets/evolution-map-reference.png` from the supplied map screenshot as a reference asset.
- Reworked the evolutionary India map outline and regional context so the peninsula, northeast, neighbouring landmasses, Sri Lanka and surrounding seas are visually clearer while retaining the existing geographic projection and interactive cyclone layers.
- Kept the map data-driven: timeline, current marker, historical track and demo prediction continue to update from the selected/user-entered observation.
