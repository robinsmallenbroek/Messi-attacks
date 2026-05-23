# Messi's Mooiste Aanvallen

Interactieve datavisualisatie van Lionel Messi's mooiste aanvallen bij FC Barcelona (2004–2021), gebouwd op StatsBomb Open Data.

## Vereisten

- Python 3.9+
- Node.js 18+ (voor de frontend)
- Git

## Setup

### 1. Repository klonen

```bash
git clone <jouw-repo-url>
cd messi-attacks
```

### 2. StatsBomb data downloaden

```bash
cd data
git clone --filter=blob:none --sparse https://github.com/statsbomb/open-data.git statsbomb-open-data
cd statsbomb-open-data
git sparse-checkout set data/competitions.json data/matches data/events data/three-sixty
cd ../..
```

> De `data/` map staat in `.gitignore` — download de data lokaal, commit hem niet.

### 3. Python pipeline

```bash
cd pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python explore_data.py
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

## Projectstructuur

```
messi-attacks/
├── pipeline/          # Python data-prep scripts
│   ├── explore_data.py
│   └── requirements.txt
├── frontend/          # Vite + React + TypeScript + D3
├── data/              # Lokale cache StatsBomb data (gitignored)
└── output/            # Verwerkte JSON-bestanden (wél in git, klein gehouden)
```
