import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import random

# ──────────────────────────────────────────────
# Page configuration
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Pokémon Combat Simulator",
    page_icon="⚔️",
    layout="wide",
)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
POPULAR_POKEMON = [
    "pikachu", "charizard", "blastoise", "venusaur", "mewtwo",
    "gengar", "dragonite", "snorlax", "gyarados", "alakazam",
    "machamp", "arcanine", "lapras", "jolteon", "starmie",
    "golem", "exeggutor", "rhydon", "tauros", "aerodactyl",
    "articuno", "zapdos", "moltres", "lucario", "garchomp",
    "eevee", "vaporeon", "flareon", "espeon", "umbreon",
]

LEVEL = 50  # Fixed level for all Pokémon


# ──────────────────────────────────────────────
# API Functions (all cached with @st.cache_data)
# ──────────────────────────────────────────────
@st.cache_data
def fetch_pokemon(name: str):
    """Fetch Pokémon data from /pokemon/{name} endpoint."""
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{name.lower().strip()}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.exceptions.RequestException:
        return None


@st.cache_data
def fetch_move(name: str):
    """Fetch move details from /move/{name} endpoint."""
    try:
        url = f"https://pokeapi.co/api/v2/move/{name}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.exceptions.RequestException:
        return None


@st.cache_data
def fetch_type(type_name: str):
    """Fetch type effectiveness data from /type/{name} endpoint."""
    try:
        url = f"https://pokeapi.co/api/v2/type/{type_name}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.exceptions.RequestException:
        return None


# ──────────────────────────────────────────────
# Data helpers
# ──────────────────────────────────────────────
def parse_pokemon(data: dict) -> dict:
    """Extract relevant fields from raw Pokémon API data."""
    return {
        "name": data["name"],
        "sprite": data["sprites"]["front_default"],
        "types": [t["type"]["name"] for t in data["types"]],
        "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
        "moves": [m["move"]["name"] for m in data["moves"]],
    }


@st.cache_data
def get_damaging_moves(move_names: tuple) -> list:
    """Return move names that have power > 0 (i.e. damaging moves).

    Checks moves in order and returns all damaging ones found
    (caps at 50 API checks for performance on first load).
    """
    damaging = []
    checked = 0
    for name in move_names:
        move_data = fetch_move(name)
        checked += 1
        if move_data and move_data.get("power") is not None and move_data["power"] > 0:
            damaging.append(name)
        # Performance guard – stop after checking 50 moves
        if checked >= 50:
            break
    return damaging


def get_type_effectiveness(move_type: str, defender_types: tuple) -> float:
    """Compute the type-effectiveness multiplier.

    Multiplies per each defender type (handles dual-type defenders).
    """
    type_data = fetch_type(move_type)
    if type_data is None:
        return 1.0

    dr = type_data["damage_relations"]
    double_damage_to = [t["name"] for t in dr["double_damage_to"]]
    half_damage_to = [t["name"] for t in dr["half_damage_to"]]
    no_damage_to = [t["name"] for t in dr["no_damage_to"]]

    effectiveness = 1.0
    for d_type in defender_types:
        if d_type in double_damage_to:
            effectiveness *= 2.0
        elif d_type in half_damage_to:
            effectiveness *= 0.5
        elif d_type in no_damage_to:
            effectiveness *= 0.0

    return effectiveness


def effectiveness_label(eff: float) -> str:
    """Human-readable label for effectiveness."""
    if eff == 0.0:
        return "No effect!"
    elif eff >= 4.0:
        return "It's ultra effective!"
    elif eff >= 2.0:
        return "It's super effective!"
    elif eff <= 0.25:
        return "It's barely effective…"
    elif eff < 1.0:
        return "It's not very effective…"
    return ""


# ──────────────────────────────────────────────
# Combat engine
# ──────────────────────────────────────────────
def calculate_damage(attacker_stats, defender_stats, defender_types, move_data):
    """Calculate damage for a single attack using the simplified formula."""
    power = move_data["power"]
    accuracy = move_data["accuracy"] if move_data["accuracy"] else 100
    move_type = move_data["type"]["name"]
    damage_class = move_data["damage_class"]["name"]

    # Choose attack / defense stats based on damage class
    if damage_class == "physical":
        atk = attacker_stats["attack"]
        dfn = defender_stats["defense"]
    else:  # special
        atk = attacker_stats["special-attack"]
        dfn = defender_stats["special-defense"]

    # Type effectiveness (tuple for hashability in cache)
    effectiveness = get_type_effectiveness(move_type, tuple(defender_types))

    # Accuracy check
    if random.random() < (accuracy / 100):
        damage = int(
            ((2 * LEVEL / 5 + 2) * power * (atk / dfn) / 50 + 2) * effectiveness
        )
    else:
        damage = 0  # miss

    missed = damage == 0 and effectiveness != 0.0
    return damage, effectiveness, missed


def simulate_battle(p1, p1_move, p2, p2_move):
    """Run a full turn-based battle. Returns (battle_log, hp_history, winner)."""
    p1_hp = p1["stats"]["hp"]
    p2_hp = p2["stats"]["hp"]

    battle_log = []  # list of dicts → pd.DataFrame later
    hp_history = [
        {"round": 0, "pokemon": p1["name"], "hp": p1_hp},
        {"round": 0, "pokemon": p2["name"], "hp": p2_hp},
    ]

    for rnd in range(1, 101):
        # Determine turn order by speed
        p1_speed = p1["stats"]["speed"]
        p2_speed = p2["stats"]["speed"]
        if p1_speed > p2_speed:
            order = [
                (p1, p1_move, p2, "p2"),
                (p2, p2_move, p1, "p1"),
            ]
        elif p2_speed > p1_speed:
            order = [
                (p2, p2_move, p1, "p1"),
                (p1, p1_move, p2, "p2"),
            ]
        else:
            if random.random() < 0.5:
                order = [
                    (p1, p1_move, p2, "p2"),
                    (p2, p2_move, p1, "p1"),
                ]
            else:
                order = [
                    (p2, p2_move, p1, "p1"),
                    (p1, p1_move, p2, "p2"),
                ]

        for attacker, atk_move, defender, def_key in order:
            dmg, eff, missed = calculate_damage(
                attacker["stats"], defender["stats"], defender["types"], atk_move
            )

            # Apply damage
            if def_key == "p1":
                p1_hp = max(0, p1_hp - dmg)
                def_hp_after = p1_hp
            else:
                p2_hp = max(0, p2_hp - dmg)
                def_hp_after = p2_hp

            eff_msg = effectiveness_label(eff)

            battle_log.append({
                "Round": rnd,
                "Attacker": attacker["name"].title(),
                "Move": atk_move["name"].replace("-", " ").title(),
                "Damage": dmg,
                "Effectiveness": eff,
                "Note": "Missed!" if missed else eff_msg,
                "Defender HP": def_hp_after,
            })

            # Check if defender fainted
            if def_hp_after <= 0:
                break

        # Record HP after this round
        hp_history.append({"round": rnd, "pokemon": p1["name"], "hp": p1_hp})
        hp_history.append({"round": rnd, "pokemon": p2["name"], "hp": p2_hp})

        if p1_hp <= 0 or p2_hp <= 0:
            break

    # Determine winner
    if p1_hp <= 0 and p2_hp <= 0:
        winner = "It's a draw!"
    elif p1_hp <= 0:
        winner = p2["name"].title()
    elif p2_hp <= 0:
        winner = p1["name"].title()
    else:
        winner = "Draw — 100-round limit reached!"

    return battle_log, hp_history, winner


# ══════════════════════════════════════════════
# STREAMLIT DASHBOARD
# ══════════════════════════════════════════════

st.title("⚔️ Pokémon Combat Simulator")
st.markdown(
    "Pick two Pokémon, choose their moves, compare stats, and simulate a battle!"
)

st.divider()

# ──────────────────────────────────────────────
# Section 1 — Pokémon Selection
# ──────────────────────────────────────────────
st.header("🎯 Select Your Pokémon")

col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    p1_choice = st.selectbox(
        "Pokémon 1",
        options=POPULAR_POKEMON,
        index=0,
        format_func=lambda x: x.title(),
        key="p1_select",
    )
    p1_custom = st.text_input(
        "Or type a custom name", key="p1_custom", placeholder="e.g. togekiss"
    )
    p1_name = p1_custom.strip().lower() if p1_custom.strip() else p1_choice

with col_sel2:
    p2_choice = st.selectbox(
        "Pokémon 2",
        options=POPULAR_POKEMON,
        index=1,
        format_func=lambda x: x.title(),
        key="p2_select",
    )
    p2_custom = st.text_input(
        "Or type a custom name", key="p2_custom", placeholder="e.g. togekiss"
    )
    p2_name = p2_custom.strip().lower() if p2_custom.strip() else p2_choice

# Fetch data
p1_data = fetch_pokemon(p1_name)
p2_data = fetch_pokemon(p2_name)

if p1_data is None:
    st.error(f"❌ Could not find Pokémon **{p1_name}**. Check the spelling and try again.")
    st.stop()
if p2_data is None:
    st.error(f"❌ Could not find Pokémon **{p2_name}**. Check the spelling and try again.")
    st.stop()

p1 = parse_pokemon(p1_data)
p2 = parse_pokemon(p2_data)

if p1["name"] == p2["name"]:
    st.warning("⚠️ Both players chose the same Pokémon — mirror match!")

st.divider()

# ──────────────────────────────────────────────
# Section 2 — Pokémon Display (sprites, name, types, stats)
# ──────────────────────────────────────────────
st.header("📋 Pokémon Profiles")

col_disp1, col_disp2 = st.columns(2)

for col, pkmn in [(col_disp1, p1), (col_disp2, p2)]:
    with col:
        st.image(pkmn["sprite"], width=160)
        st.subheader(pkmn["name"].title())
        type_badges = " / ".join(t.title() for t in pkmn["types"])
        st.markdown(f"**Types:** {type_badges}")
        for stat_name, stat_val in pkmn["stats"].items():
            st.write(f"**{stat_name.replace('-', ' ').title()}:** {stat_val}")

st.divider()

# ──────────────────────────────────────────────
# Section 3 — Move Selection (damaging moves only)
# ──────────────────────────────────────────────
st.header("💥 Select Moves")

with st.spinner("Loading available damaging moves… (cached after first load)"):
    p1_damaging = get_damaging_moves(tuple(p1["moves"]))
    p2_damaging = get_damaging_moves(tuple(p2["moves"]))

if not p1_damaging:
    st.error(f"No damaging moves found for **{p1['name'].title()}**.")
    st.stop()
if not p2_damaging:
    st.error(f"No damaging moves found for **{p2['name'].title()}**.")
    st.stop()

col_mv1, col_mv2 = st.columns(2)

with col_mv1:
    p1_move_name = st.selectbox(
        f"{p1['name'].title()}'s Move",
        options=p1_damaging,
        format_func=lambda x: x.replace("-", " ").title(),
        key="p1_move",
    )
    p1_move_data = fetch_move(p1_move_name)
    st.markdown(
        f"**Power:** {p1_move_data['power']}  \n"
        f"**Accuracy:** {p1_move_data['accuracy']}  \n"
        f"**Type:** {p1_move_data['type']['name'].title()}  \n"
        f"**Class:** {p1_move_data['damage_class']['name'].title()}"
    )

with col_mv2:
    p2_move_name = st.selectbox(
        f"{p2['name'].title()}'s Move",
        options=p2_damaging,
        format_func=lambda x: x.replace("-", " ").title(),
        key="p2_move",
    )
    p2_move_data = fetch_move(p2_move_name)
    st.markdown(
        f"**Power:** {p2_move_data['power']}  \n"
        f"**Accuracy:** {p2_move_data['accuracy']}  \n"
        f"**Type:** {p2_move_data['type']['name'].title()}  \n"
        f"**Class:** {p2_move_data['damage_class']['name'].title()}"
    )

st.divider()

# ──────────────────────────────────────────────
# Section 4 — Stat Comparison Chart (Plotly grouped bar)
# ──────────────────────────────────────────────
st.header("📊 Stat Comparison")

stat_df = pd.DataFrame([
    {"pokemon": p1["name"].title(), **p1["stats"]},
    {"pokemon": p2["name"].title(), **p2["stats"]},
])

melted = stat_df.melt(id_vars="pokemon", var_name="stat", value_name="value")

fig_stats = px.bar(
    melted,
    x="stat",
    y="value",
    color="pokemon",
    barmode="group",
    title="Base Stats Comparison",
    labels={"stat": "Stat", "value": "Value", "pokemon": "Pokémon"},
    color_discrete_sequence=["#ef5350", "#42a5f5"],
)
fig_stats.update_layout(
    xaxis_tickangle=-30,
    legend_title_text="Pokémon",
)
st.plotly_chart(fig_stats, use_container_width=True)

st.divider()

# ──────────────────────────────────────────────
# Section 5 — Battle Simulation
# ──────────────────────────────────────────────
st.header("⚔️ Battle!")

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    battle_pressed = st.button("⚔️ Start Battle!", use_container_width=True)
with col_btn2:
    rematch_pressed = st.button("🔄 Rematch", use_container_width=True)

if battle_pressed or rematch_pressed:
    battle_log, hp_history, winner = simulate_battle(p1, p1_move_data, p2, p2_move_data)
    st.session_state["battle_log"] = battle_log
    st.session_state["hp_history"] = hp_history
    st.session_state["winner"] = winner

if "battle_log" in st.session_state:
    winner = st.session_state["winner"]
    battle_log = st.session_state["battle_log"]
    hp_history = st.session_state["hp_history"]

    # Winner announcement
    if "draw" in winner.lower():
        st.warning(f"🤝 {winner}")
    else:
        st.success(f"🏆 **{winner}** wins the battle!")

    # Battle log table
    st.subheader("📜 Battle Log")
    log_df = pd.DataFrame(battle_log)
    st.dataframe(log_df, use_container_width=True, hide_index=True)

    st.divider()

    # ──────────────────────────────────────────
    # Section 6 — HP Over Time Chart
    # ──────────────────────────────────────────
    st.header("📉 HP Over Time")

    hp_df = pd.DataFrame(hp_history)
    fig_hp = px.line(
        hp_df,
        x="round",
        y="hp",
        color="pokemon",
        title="HP Remaining Each Round",
        labels={"round": "Round", "hp": "HP", "pokemon": "Pokémon"},
        markers=True,
        color_discrete_sequence=["#ef5350", "#42a5f5"],
    )
    fig_hp.update_layout(legend_title_text="Pokémon")
    st.plotly_chart(fig_hp, use_container_width=True)
