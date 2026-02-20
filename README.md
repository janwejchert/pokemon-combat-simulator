# ⚔️ Pokémon Combat Simulator

An interactive Streamlit dashboard that lets you pick two Pokémon, compare their stats, choose moves, and simulate a turn-based battle — all powered by live data from the [PokéAPI](https://pokeapi.co/).

## 🚀 Deployed App

👉 **[Click here to open the app](https://pokemon-combat-simulator.streamlit.app)**

*(Update this URL if your Streamlit Community Cloud link differs after deployment.)*

## ✨ Features

- **Pokémon Selection** — Choose from 30 popular Pokémon or type any name
- **Live API Data** — Sprites, stats, types, and moves fetched from PokéAPI
- **Move Filtering** — Only damaging moves (power > 0) are shown
- **Stat Comparison** — Interactive Plotly grouped bar chart
- **Battle Simulation** — Turn-based combat with type effectiveness, accuracy checks, and speed-based turn order
- **Battle Log** — Round-by-round table of every attack
- **HP Over Time** — Plotly line chart tracking both Pokémon's HP across rounds
- **Caching** — All API calls cached with `@st.cache_data` for fast reloads

## 📦 Setup (Local)

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## 🤝 Contributions

| Member | Contributions |
|--------|--------------|
| Member 1 | *Describe contributions here* |
| Member 2 | *Describe contributions here* |
| Member 3 | *Describe contributions here* |
