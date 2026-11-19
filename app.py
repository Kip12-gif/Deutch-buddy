import io
import json
import re
import time
from pathlib import Path
import streamlit as st
from deep_translator import MyMemoryTranslator
from gtts import gTTS

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DeutschBuddy | English → German",
    page_icon="🇩🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS (LIGHT GREEN HEADERS & CLEAN CARD UI) ---
st.markdown(
    """
<style>
    .main-title {
        color: #82E0AA;
        font-size: 2.4rem;
        font-weight: 800;
        margin-bottom: 2px;
    }
    .sub-title {
        color: #A3E4D7;
        font-size: 1.08rem;
        margin-bottom: 20px;
    }
    h1, h2, h3, h4 {
        color: #82E0AA !important;
    }
    .output-card {
        background-color: #1A1F2C;
        border-left: 5px solid #2ECC71;
        padding: 20px;
        border-radius: 10px;
        margin-top: 8px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.28);
    }
    .german-text {
        font-size: 1.55rem;
        font-weight: 600;
        color: #FFFFFF;
        line-height: 1.4;
    }
    .meta-note {
        color: #A3E4D7;
        font-size: 0.9rem;
        margin-top: 8px;
    }
    .source-pill {
        display: inline-block;
        background-color: #145A32;
        color: #82E0AA;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .badge-der {
        background-color: #2980B9;
        color: #FFFFFF;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-die {
        background-color: #C0392B;
        color: #FFFFFF;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-das {
        background-color: #27AE60;
        color: #FFFFFF;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-neutral {
        background-color: #34495E;
        color: #ECF0F1;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .flashcard {
        background-color: #161B22;
        border: 1px solid #30363D;
        padding: 11px;
        border-radius: 8px;
        margin-bottom: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- SESSION STATE ---
if "saved_phrases" not in st.session_state:
    st.session_state.saved_phrases = []
if "english_draft" not in st.session_state:
    st.session_state.english_draft = ""
if "active_result" not in st.session_state:
    st.session_state.active_result = None

DIALECT_MAP = {
    "Standard German (Germany)": "de-DE",
    "Austrian German": "de-AT",
    "Swiss German": "de-CH",
}


# --- DATA LOADING (UTF-8-SIG SAFE & ERROR-RESILIENT) ---
def resolve_data_path(filename: str) -> Path | None:
    base_dir = Path(__file__).parent
    candidates = [base_dir / "data" / filename, base_dir / filename]
    for path in candidates:
        if path.exists():
            return path
    return None


def safe_load_json(filename: str, fallback):
    path = resolve_data_path(filename)
    if not path:
        return fallback, f"{filename} not found (using built-in fallback)."
    try:
        # utf-8-sig automatically strips any UTF-8 Byte Order Mark (BOM)
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, type(fallback)):
            return fallback, f"{filename} had an unexpected JSON structure (using fallback)."
        return data, None
    except Exception as exc:
        return fallback, f"Could not parse {filename}: {exc}"


FALLBACK_PHRASES = [
    {
        "id": "greet_1",
        "category": "Greetings & Politeness",
        "en": "Hello, how are you?",
        "du": "Hallo, wie geht es dir?",
        "sie": "Guten Tag, wie geht es Ihnen?",
        "note": "Built-in fallback phrase while phrases.json is being checked.",
    },
    {
        "id": "cafe_1",
        "category": "Café & Dining",
        "en": "Could I please have a large coffee with oat milk?",
        "du": "Kann ich bitte einen großen Kaffee mit Hafermilch haben?",
        "sie": "Könnte ich bitte einen großen Kaffee mit Hafermilch haben?",
        "note": "'Könnte' sounds polite and natural when ordering.",
    },
]

FALLBACK_DICT = {
    "coffee": {"de": "Kaffee", "pos": "noun", "article": "der", "plural": "Kaffees"},
    "water": {"de": "Wasser", "pos": "noun", "article": "das", "plural": "Wässer"},
    "train": {"de": "Zug", "pos": "noun", "article": "der", "plural": "Züge"},
}


@st.cache_data(show_spinner=False)
def load_offline_resources() -> tuple[list[dict], dict, list[str]]:
    warnings: list[str] = []
    phrases, p_warn = safe_load_json("phrases.json", FALLBACK_PHRASES)
    if p_warn:
        warnings.append(p_warn)

    dictionary, d_warn = safe_load_json("dictionary.json", FALLBACK_DICT)
    if d_warn:
        warnings.append(d_warn)

    return phrases, dictionary, warnings


PHRASES_DATA, DICT_DATA, DATA_WARNINGS = load_offline_resources()


# --- TEXT NORMALIZATION & LOOKUP HELPERS ---
def normalize_text(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[^\w\s']", "", cleaned)
    return re.sub(r"\s+", " ", cleaned)


def extract_known_words_from_en(english_text: str, dictionary: dict) -> list[dict]:
    tokens = re.findall(r"[a-zA-Z']+", english_text.lower())
    found: list[dict] = []
    seen = set()
    for tok in tokens:
        if tok in seen:
            continue
        if tok in dictionary:
            seen.add(tok)
            item = dictionary[tok]
            found.append(
                {
                    "en": tok,
                    "de": item.get("de", ""),
                    "pos": item.get("pos", ""),
                    "article": item.get("article", ""),
                    "plural": item.get("plural", ""),
                }
            )
    return found


def lookup_phrasebook(english_text: str, tone: str, phrases: list[dict]) -> dict | None:
    norm_query = normalize_text(english_text)
    if not norm_query:
        return None

    for entry in phrases:
        if normalize_text(entry.get("en", "")) == norm_query:
            german = entry.get("du") if tone == "Informal (Du)" else entry.get("sie")
            if not german:
                german = entry.get("du") or entry.get("sie") or ""
            return {
                "en": entry.get("en", english_text),
                "de": german,
                "source": f"Offline Phrasebook • {entry.get('category', 'General')}",
                "note": entry.get("note", ""),
                "matched_words": extract_known_words_from_en(english_text, DICT_DATA),
            }
    return None


def lookup_dictionary(english_text: str, dictionary: dict) -> dict | None:
    tokens = re.findall(r"[a-zA-Z']+", english_text.lower())
    if not tokens:
        return None

    if len(tokens) == 1 and tokens[0] in dictionary:
        entry = dictionary[tokens[0]]
        article = entry.get("article", "")
        de_word = entry.get("de", "")
        display_de = f"{article} {de_word}".strip() if article else de_word
        return {
            "en": english_text.strip(),
            "de": display_de,
            "source": "Offline Dictionary • Exact Word Match",
            "note": f"Part of speech: {entry.get('pos', 'word')}"
            + (f" • Plural: {entry['plural']}" if entry.get("plural") else ""),
            "matched_words": [
                {
                    "en": tokens[0],
                    "de": de_word,
                    "pos": entry.get("pos", ""),
                    "article": article,
                    "plural": entry.get("plural", ""),
                }
            ],
        }

    matched_words = extract_known_words_from_en(english_text, dictionary)
    if matched_words:
        glossed_tokens = []
        for tok in tokens:
            if tok in dictionary:
                item = dictionary[tok]
                art = item.get("article", "")
                word = item.get("de", tok)
                glossed_tokens.append(f"{art} {word}".strip() if art else word)
            else:
                glossed_tokens.append(f"[{tok}]")
        return {
            "en": english_text.strip(),
            "de": " ".join(glossed_tokens),
            "source": "Offline Dictionary • Word-by-Word Gloss",
            "note": "Bracketed words [like this] were not in the offline dictionary yet.",
            "matched_words": matched_words,
        }

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def live_translate_fallback(text: str, target_locale: str) -> str:
    time.sleep(0.25)
    return MyMemoryTranslator(source="en-GB", target=target_locale).translate(text.strip())


@st.cache_data(ttl=3600, show_spinner=False)
def generate_audio(german_text: str, slow_mode: bool = False) -> bytes:
    clean_speech = re.sub(r"\[([^\]]+)\]", r"\1", german_text)
    tts = gTTS(text=clean_speech, lang="de", slow=slow_mode)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()


def build_flashcards_csv(cards: list[dict]) -> str:
    lines = ["English,German,Tone,Source"]
    for c in cards:
        en_esc = '"' + c["en"].replace('"', '""') + '"'
        de_esc = '"' + c["de"].replace('"', '""') + '"'
        tone_esc = '"' + c["tone"].replace('"', '""') + '"'
        src_esc = '"' + c["source"].replace('"', '""') + '"'
        lines.append(f"{en_esc},{de_esc},{tone_esc},{src_esc}")
    return "\n".join(lines)


def set_example(phrase: str) -> None:
    st.session_state.english_draft = phrase
    st.session_state.english_input_box = phrase


def render_gender_badge(article: str, pos: str) -> str:
    if article == "der":
        return '<span class="badge-der">der</span>'
    if article == "die":
        return '<span class="badge-die">die</span>'
    if article == "das":
        return '<span class="badge-das">das</span>'
    label = pos if pos else "word"
    return f'<span class="badge-neutral">{label}</span>'


# --- SIDEBAR: SETTINGS, DATA STATUS & SAVED FLASHCARDS ---
with st.sidebar:
    st.markdown("### Learning Settings")
    tone = st.radio(
        "Address Formality",
        options=["Informal (Du)", "Formal (Sie)"],
        help="Selects authentic 'du' or 'Sie' variants from the offline phrasebook.",
    )
    dialect_label = st.selectbox(
        "German Variant (Live Fallback)",
        options=list(DIALECT_MAP.keys()),
        index=0,
    )
    slow_audio = st.checkbox("Slower pronunciation (learner mode)", value=False)
    use_online_fallback = st.checkbox(
        "Enable live online fallback for unknown sentences",
        value=True,
        help="Uses MyMemory only when a phrase is not found in phrases.json or dictionary.json.",
    )

    st.markdown("---")
    st.markdown("### Offline Data Status")
    st.caption(
        f"Phrasebook loaded: **{len(PHRASES_DATA)}** phrases • "
        f"Dictionary loaded: **{len(DICT_DATA)}** words"
    )
    for warn in DATA_WARNINGS:
        st.caption(f"⚠️ {warn}")

    st.markdown("---")
    st.markdown("### Noun Gender Key")
    st.markdown(
        '<span class="badge-der">der</span> Masculine &nbsp; '
        '<span class="badge-die">die</span> Feminine &nbsp; '
        '<span class="badge-das">das</span> Neuter',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(f"### Saved Flashcards ({len(st.session_state.saved_phrases)})")
    if st.session_state.saved_phrases:
        for item in reversed(st.session_state.saved_phrases):
            st.markdown(
                f'<div class="flashcard">'
                f'<b>EN:</b> {item["en"]}<br>'
                f'<b>DE:</b> <span style="color:#82E0AA;">{item["de"]}</span><br>'
                f'<small style="color:#8B949E;">{item["tone"]}</small>'
                f"</div>",
                unsafe_allow_html=True,
            )

        csv_data = build_flashcards_csv(st.session_state.saved_phrases)
        st.download_button(
            label="Download Flashcards (CSV)",
            data=csv_data,
            file_name="deutsch_flashcards.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if st.button("Clear Saved Phrases", use_container_width=True):
            st.session_state.saved_phrases = []
            st.rerun()
    else:
        st.caption("Translate a word or phrase and click Save Flashcard to build your deck.")

# --- MAIN HEADER ---
st.markdown('<div class="main-title">🇩🇪 DeutschBuddy</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Offline-First English → German Translator & Interactive Study Companion</div>',
    unsafe_allow_html=True,
)

# --- TABS: TRANSLATOR & PHRASEBOOK BROWSER ---
tab_translate, tab_phrasebook = st.tabs(["Translator & Lookup", "Starter Phrasebook"])

with tab_translate:
    st.caption("Try an instant offline phrase:")
    ex1, ex2, ex3 = st.columns(3)
    ex1.button(
        "☕ Ordering coffee",
        use_container_width=True,
        on_click=set_example,
        args=("Could I please have a large coffee with oat milk?",),
    )
    ex2.button(
        "🚉 Asking for directions",
        use_container_width=True,
        on_click=set_example,
        args=("Excuse me, how do I get to the central train station?",),
    )
    ex3.button(
        "🤝 Meeting someone",
        use_container_width=True,
        on_click=set_example,
        args=("Nice to meet you! Where are you from?",),
    )

    st.markdown("---")

    col_in, col_out = st.columns(2, gap="large")

    with col_in:
        st.markdown("#### English Input")
        if "english_input_box" not in st.session_state:
            st.session_state.english_input_box = st.session_state.english_draft

        english_input = st.text_area(
            label="Enter English word or phrase",
            key="english_input_box",
            height=165,
            placeholder="Try a single word (e.g., coffee, station, train) or a full phrase...",
            label_visibility="collapsed",
        )

        btn_col1, btn_col2 = st.columns([3, 1])
        translate_clicked = btn_col1.button(
            "Translate to Deutsch ✨", type="primary", use_container_width=True
        )
        clear_clicked = btn_col2.button("Clear", use_container_width=True)

        if clear_clicked:
            st.session_state.english_draft = ""
            st.session_state.active_result = None
            st.rerun()

        should_run = translate_clicked or (
            english_input.strip()
            and english_input.strip() != st.session_state.english_draft
        )

        if should_run:
            query = english_input.strip()
            if not query:
                st.warning("Please enter an English word or phrase first.")
            else:
                st.session_state.english_draft = query
                result = lookup_phrasebook(query, tone, PHRASES_DATA)
                dict_result = lookup_dictionary(query, DICT_DATA)

                if result is None and dict_result and "Exact Word Match" in dict_result["source"]:
                    result = dict_result

                if result is None and use_online_fallback:
                    try:
                        with st.spinner("Checking online translator..."):
                            online_de = live_translate_fallback(query, DIALECT_MAP[dialect_label])
                        result = {
                            "en": query,
                            "de": online_de,
                            "source": f"Online Translator • {dialect_label}",
                            "note": "Translated via live fallback because this full sentence wasn't in phrases.json.",
                            "matched_words": extract_known_words_from_en(query, DICT_DATA),
                        }
                    except Exception:
                        result = dict_result

                if result is None:
                    result = dict_result or {
                        "en": query,
                        "de": "No offline match found",
                        "source": "Offline Lookup",
                        "note": "Try a single dictionary word (e.g., 'water', 'train', 'hotel') or enable live online fallback in the sidebar.",
                        "matched_words": [],
                    }

                st.session_state.active_result = result

    with col_out:
        st.markdown(f"#### Deutsch Output ({tone})")

        active = st.session_state.active_result
        if active:
            refreshed = lookup_phrasebook(active["en"], tone, PHRASES_DATA)
            if refreshed:
                active = refreshed
                st.session_state.active_result = refreshed

            st.markdown(
                f"""
                <div class="output-card">
                    <span class="source-pill">{active["source"]}</span>
                    <div class="german-text">{active["de"]}</div>
                    <div class="meta-note">{active["note"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if active["de"] != "No offline match found":
                act1, act2 = st.columns([2, 1])
                with act1:
                    try:
                        audio_bytes = generate_audio(active["de"], slow_mode=slow_audio)
                        st.audio(audio_bytes, format="audio/mp3")
                    except Exception as audio_err:
                        st.caption(f"Audio unavailable right now: {audio_err}")

                with act2:
                    if st.button("⭐ Save Flashcard", use_container_width=True):
                        entry = {
                            "en": active["en"],
                            "de": active["de"],
                            "tone": tone,
                            "source": active["source"],
                        }
                        if entry not in st.session_state.saved_phrases:
                            st.session_state.saved_phrases.append(entry)
                            st.toast("Saved to your study deck!", icon="✅")
                        else:
                            st.toast("Already in your flashcards.", icon="ℹ️")

            matched_words = active.get("matched_words", [])
            if matched_words:
                with st.expander("Vocabulary & Noun Gender Breakdown", expanded=True):
                    for w in matched_words:
                        badge = render_gender_badge(w.get("article", ""), w.get("pos", ""))
                        plural_txt = (
                            f" • *Plural:* {w['plural']}"
                            if w.get("plural") and w["plural"] != "—"
                            else ""
                        )
                        st.markdown(
                            f"{badge} &nbsp; **{w['de']}** (*{w['en']}*){plural_txt}",
                            unsafe_allow_html=True,
                        )
        else:
            st.markdown(
                """
                <div class="output-card" style="opacity: 0.65;">
                    <div class="german-text">Deine Übersetzung erscheint hier...</div>
                    <div class="meta-note">Click a starter phrase above or type any English word or sentence.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with tab_phrasebook:
    st.markdown("#### Browse Curated Offline Phrases")
    if not PHRASES_DATA:
        st.warning("No phrases.json file was detected in your repository.")
    else:
        categories = ["All Categories"] + sorted(
            {p.get("category", "General") for p in PHRASES_DATA}
        )
        selected_cat = st.selectbox("Filter by Category", options=categories)

        filtered = [
            p
            for p in PHRASES_DATA
            if selected_cat == "All Categories" or p.get("category") == selected_cat
        ]

        for item in filtered:
            german_line = item.get("du") if tone == "Informal (Du)" else item.get("sie")
            st.markdown(
                f"""
                <div class="output-card">
                    <span class="source-pill">{item.get("category", "General")} • {tone}</span>
                    <div style="color:#A3E4D7; font-size:0.95rem; margin-bottom:4px;">🇬🇧 {item.get("en", "")}</div>
                    <div class="german-text">🇩🇪 {german_line or ""}</div>
                    <div class="meta-note">💡 {item.get("note", "")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
