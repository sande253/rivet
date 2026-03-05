# Split Monolithic Dashboard into Separate Pages

## Overview
Refactor the 2553-line `index.html` into separate page files while keeping all existing styling, functionality, and design intact. This is a structural reorganization only - no visual changes.

## Goal
Split the single-page application into multiple Flask routes and templates to improve maintainability and reduce file size, while preserving 100% of current functionality and appearance.

## Current State
- Single monolithic file: `application/templates/index.html` (2553 lines)
- All pages embedded in one file with JavaScript-based page switching
- Pages: Home, Analyze, Market, How It Works, Account, My Analyses
- Single route serves everything: `/` (index route)

## Target State
- Separate template files for each page
- Separate Flask routes for each page
- Shared base template with common elements (nav, footer, styles, scripts)
- All existing CSS and JavaScript preserved
- Same user experience and visual design

---

## Requirements

### REQ-1: Create Base Template
**Priority:** High  
**Description:** Extract common elements into a base template that all pages will extend

**Acceptance Criteria:**
- Create `application/templates/base.html` containing:
  - All `<head>` content (meta tags, title, CSS links, inline styles)
  - Top navigation bar (`.topnav`)
  - Footer
  - All JavaScript code (language switching, utilities, etc.)
  - Jinja2 blocks for page-specific content
- Base template must include all existing CSS (keep inline in `<style>` tags)
- Base template must include all existing JavaScript (keep inline in `<script>` tags)

### REQ-2: Create Home Page Template
**Priority:** High  
**Description:** Extract home page content into separate template

**Acceptance Criteria:**
- Create `application/templates/home.html` that extends `base.html`
- Contains only the home page content:
  - Hero section (`.home-hero`)
  - Feature cards (`.home-cards-wrap`)
  - Recent analyses section (`.recent-section`)
- No changes to HTML structure or classes
- Route: `/` or `/home`

### REQ-3: Create Analyze Page Template
**Priority:** High  
**Description:** Extract analyze page content into separate template

**Acceptance Criteria:**
- Create `application/templates/analyze.html` that extends `base.html`
- Contains the analyze page content (`.analyze-page-wrap`)
- Includes sidebar, form, results sections
- All existing JavaScript for analysis functionality preserved
- Route: `/analyze`

### REQ-4: Create Market Page Template
**Priority:** Medium  
**Description:** Extract market intelligence page into separate template

**Acceptance Criteria:**
- Create `application/templates/market.html` that extends `base.html`
- Contains market page content (`#page-market`)
- All market data and charts preserved
- Route: `/market`

### REQ-5: Create How It Works Page Template
**Priority:** Medium  
**Description:** Extract "How It Works" page into separate template

**Acceptance Criteria:**
- Create `application/templates/how.html` that extends `base.html`
- Contains how-it-works content (`#page-how`)
- Route: `/how`

### REQ-6: Create Account Page Template
**Priority:** Low  
**Description:** Extract account page into separate template

**Acceptance Criteria:**
- Create `application/templates/account.html` that extends `base.html`
- Contains account page content (`#page-account`)
- Route: `/account`

### REQ-7: Create My Analyses Page Template
**Priority:** Low  
**Description:** Extract analyses history page into separate template

**Acceptance Criteria:**
- Create `application/templates/analyses.html` that extends `base.html`
- Contains analyses list content (`#page-analyses`)
- Route: `/analyses`

### REQ-8: Update Navigation Links
**Priority:** High  
**Description:** Replace JavaScript page switching with proper href links

**Acceptance Criteria:**
- Update all `onclick="showPage('...')"` to proper `href` attributes
- Navigation links point to new routes:
  - Home: `/` or `/home`
  - Analyze: `/analyze`
  - Market: `/market`
  - How: `/how`
  - Account: `/account`
  - Analyses: `/analyses`
- Active page highlighting still works (use Flask's `request.path`)

### REQ-9: Create Flask Routes
**Priority:** High  
**Description:** Add new routes to serve the separate pages

**Acceptance Criteria:**
- Create or update `application/src/routes/pages.py` with routes:
  - `@pages_bp.route('/')` → `home.html`
  - `@pages_bp.route('/home')` → `home.html`
  - `@pages_bp.route('/analyze')` → `analyze.html`
  - `@pages_bp.route('/market')` → `market.html`
  - `@pages_bp.route('/how')` → `how.html`
  - `@pages_bp.route('/account')` → `account.html` (login required)
  - `@pages_bp.route('/analyses')` → `analyses.html` (login required)
- Register blueprint in `application/src/app.py`
- All routes use `@login_required` where appropriate

### REQ-10: Remove Page Switching JavaScript
**Priority:** Medium  
**Description:** Clean up JavaScript that's no longer needed

**Acceptance Criteria:**
- Remove `showPage()` function (no longer needed)
- Remove `.page`, `.page.active`, `.fade-in`, `.fade-out` CSS classes
- Remove `currentPage` variable
- Keep all other JavaScript (analysis, mockup, language switching, etc.)

### REQ-11: Preserve All Functionality
**Priority:** Critical  
**Description:** Ensure zero functionality loss

**Acceptance Criteria:**
- Language switching (EN/TE) works on all pages
- Analysis form submission works
- Mockup generation works
- Market data displays correctly
- User dropdown menu works
- All animations and transitions preserved
- Mobile responsiveness unchanged

### REQ-12: Testing & Validation
**Priority:** High  
**Description:** Verify the refactor works correctly

**Acceptance Criteria:**
- All pages load without errors
- Navigation between pages works
- Analysis workflow completes successfully
- Mockup generation works
- No console errors
- No broken styles
- No broken links

---

## Design

### File Structure
```
application/templates/
├── base.html              # Base template with nav, footer, styles, scripts
├── home.html              # Home page (extends base)
├── analyze.html           # Analyze page (extends base)
├── market.html            # Market page (extends base)
├── how.html               # How it works (extends base)
├── account.html           # Account page (extends base)
├── analyses.html          # My analyses (extends base)
└── auth/
    ├── login.html
    └── signup.html
```

### Routes Structure
```python
# application/src/routes/pages.py
from flask import Blueprint, render_template
from flask_login import login_required

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
@pages_bp.route('/home')
def home():
    return render_template('home.html')

@pages_bp.route('/analyze')
@login_required
def analyze():
    return render_template('analyze.html')

@pages_bp.route('/market')
def market():
    return render_template('market.html')

@pages_bp.route('/how')
def how():
    return render_template('how.html')

@pages_bp.route('/account')
@login_required
def account():
    return render_template('account.html')

@pages_bp.route('/analyses')
@login_required
def analyses():
    return render_template('analyses.html')
```

### Base Template Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <!-- All meta tags, title, CSS links -->
  <style>
    /* ALL existing CSS from index.html */
  </style>
</head>
<body>
  <!-- Top navigation -->
  <nav class="topnav">
    <!-- Nav content with proper href links -->
  </nav>

  <!-- Page content block -->
  <div class="page-shell">
    {% block content %}{% endblock %}
  </div>

  <!-- Footer -->
  <footer>
    <!-- Footer content -->
  </footer>

  <!-- All JavaScript -->
  <script>
    /* ALL existing JavaScript */
  </script>
</body>
</html>
```

### Page Template Structure
```html
{% extends "base.html" %}

{% block content %}
  <!-- Page-specific content only -->
{% endblock %}
```

---

## Implementation Plan

### Phase 1: Create Base Template
1. Create `base.html`
2. Copy all `<head>` content from `index.html`
3. Copy navigation bar
4. Copy footer
5. Copy all `<style>` tags
6. Copy all `<script>` tags
7. Add `{% block content %}{% endblock %}`

### Phase 2: Create Page Templates
1. Create `home.html` - extract home page content
2. Create `analyze.html` - extract analyze page content
3. Create `market.html` - extract market page content
4. Create `how.html` - extract how-it-works content
5. Create `account.html` - extract account content
6. Create `analyses.html` - extract analyses content

### Phase 3: Update Navigation
1. Replace all `onclick="showPage(...)"` with `href="..."`
2. Update active page logic to use Flask's `request.path`
3. Test navigation between pages

### Phase 4: Create Routes
1. Create `application/src/routes/pages.py`
2. Add all page routes
3. Register blueprint in `app.py`
4. Test all routes

### Phase 5: Cleanup
1. Remove `showPage()` function
2. Remove page switching CSS
3. Remove unused variables
4. Test everything

### Phase 6: Testing
1. Test all pages load
2. Test navigation
3. Test analysis workflow
4. Test mockup generation
5. Test language switching
6. Test on mobile

---

## Migration Strategy

### Approach: Parallel Development
- Keep existing `index.html` as fallback
- Create new templates alongside
- Switch routes when ready
- Can rollback if issues found

### Rollback Plan
- If issues occur, revert route changes
- Old `index.html` still works
- Zero downtime

---

## Success Criteria

1. All pages accessible via separate URLs
2. Zero visual changes to user interface
3. All functionality works identically
4. No console errors
5. No broken links or images
6. Mobile responsiveness maintained
7. Language switching works on all pages
8. Analysis and mockup workflows complete successfully

---

## Notes

- This is a STRUCTURAL refactor only - NO visual changes
- All existing CSS stays inline in base template
- All existing JavaScript stays inline in base template
- No new dependencies required
- No database changes needed
- No API changes needed

---

## Status: ✅ COMPLETED

All phases completed successfully. The monolithic index.html has been split into separate page templates while preserving all styling and functionality.

### Completion Summary

✅ Phase 1: Base template created with all common elements
✅ Phase 2: All page templates created (home, analyze, market, how, account, analyses)
✅ Phase 3: Navigation updated from onclick to href
✅ Phase 4: Flask routes created and registered
✅ Phase 5: Page switching JavaScript removed
✅ Phase 6: Tested and verified working

### Files Created
- `application/templates/base.html` - Base template
- `application/templates/home.html` - Home page
- `application/templates/analyze.html` - Analyze page
- `application/templates/market.html` - Market page
- `application/templates/how.html` - How it works page
- `application/templates/account.html` - Account page
- `application/templates/analyses.html` - My analyses page
- `application/src/routes/pages.py` - Page routes blueprint
- `application/templates/index_backup.html` - Backup of original

### Changes Made
- Replaced `ui_bp` with `pages_bp` in route registration
- Updated all navigation links from `onclick` to `href`
- Removed page switching JavaScript and CSS
- All functionality preserved and tested

See `REFACTOR_SUMMARY.md` for detailed documentation.
