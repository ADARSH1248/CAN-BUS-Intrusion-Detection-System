# CAN Bus Intrusion Detection System
### Machine Learning Based Vehicle Network Security
**Final Year Engineering Project — NMAM Institute of Technology**
**Dept. of Computer Science | Designed by Adarsh Bhat**

---

## Project Structure

```
CAN Bus Intrusion Detection System/
│
├── app.py                    ← Flask entry point (to be implemented)
│
├── templates/
│   ├── index.html            ← Home / Landing page
│   ├── upload.html           ← Dataset upload page + processing overlay
│   └── dashboard.html        ← Result dashboard with sidebar
│
├── static/
│   ├── css/
│   │   └── style.css         ← Master stylesheet (dark glassmorphism theme)
│   ├── js/
│   │   └── script.js         ← All JS: canvas, upload, charts, table, sidebar
│   └── images/               ← Place any project images here
│
└── README.md
```

## How to Run (with Flask)

```bash
pip install flask
python app.py
```

Then open: http://localhost:5000

## Pages

| Page | File | Description |
|------|------|-------------|
| Home | `index.html` | Landing page with hero, about, features, contact |
| Upload | `upload.html` | CSV drag-&-drop upload with processing animation |
| Dashboard | `dashboard.html` | Stats, charts, vehicle status, predictions table |

## Tech Stack

- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript (vanilla)
- **Icons**: Font Awesome 6
- **Charts**: Chart.js 4
- **Backend** *(future)*: Python Flask + Scikit-learn / XGBoost

## Design Theme

- Dark background: `#050d1a`
- Navy accents: `#0a1628`
- Cyan highlights: `#00d4ff`
- Glassmorphism cards with animated network canvas background
