import streamlit as st
from gtts import gTTS
import io
from google import genai

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DeutschBuddy | English → German",
    page_icon="🇩🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR PLEASING UI ---
st.markdown("""
<style>
    .main-title {
        color: #82E0AA;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0px;
    }
    .sub-title {
        color: #A3E4D7;
        font-size: 1.1rem;
        margin-bottom: 25px;
    }
    .output-card {
        background-color: #1A1F2C;
        border-left: 5px solid #2ECC71;
        padding: 20px;
        border-radius: 10px;
        margin-top: 10px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .german-text {
        font-size: 1.6rem;
        font-weight: 600;
        color: #FFFFFF;
    }
    .badge-der { background-color: #2980B9; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-die { background-color: #C0392B; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-das { background-color: #27AE60; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .flashcard {
        background-color: #161B22;
        border: 1px solid #30363D;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if "saved_phrases" not in st.session_state:
    st.session_state.saved_phrases = []

# --- HELPER FUNCTIONS ---
def generate_audio(german_text: str):
    tts = gTTS(text=german_text, lang="de", slow=False)
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp

@st.cache_data(ttl=3600, show_spinner=False)
def translate_with_gemini(english_text: str, tone: str, api_key: str):
    """Translates English to German using Gemini with precise formality and grammar breakdown."""
    client = genai.Client(api_key=api_key)
    prompt = f"""
    You are an expert German language translator and tutor.
    Translate this English text into German using the requested formality tone:
    English: "{english_text}"
    Formality Tone: {tone} (Informal 'du' vs Formal 'Sie')

    Provide your response in this exact format:
    ---TRANSLATION---
    [The precise German translation only]
    ---BREAKDOWN---
    [1. **Key Vocabulary & Noun Genders:** List important nouns with their article (der/die/das) and plural form.
    2. **Quick Grammar Tip:** One short, practical tip about word order or structure used here.]
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    
    text = response.text
    if "---TRANSLATION---" in text and "---BREAKDOWN---" in text:
        parts = text.split("---BREAKDOWN---")
        german_part = parts[0].replace("---TRANSLATION---", "").strip()
        breakdown_part = parts[1].strip()
        return german_part, breakdown_part
    else:
        return text.strip(), "Breakdown unavailable."

# --- SIDEBAR: SETTINGS & SAVED FLASHCARDS ---
with st.sidebar:
    st.markdown("### ⚙️ Learning Settings")
    tone = st.radio(
        "Address Formality:",
        options=["Informal (Du)", "Formal (Sie)"],
        help="German distinguishes between casual ('du') and polite/professional ('Sie') speech."
    )
    
    st.markdown("---")
    st.markdown("### 🔑 Gemini API Key")
    gemini_key = st.text_input(
        "Enter API Key",
        type="password",
        help="Required to power the translator and AI tutor. Get a free key at aistudio.google.com"
    )

    st.markdown("---")
    st.markdown("### 📚 Gender Color Guide")
    st.markdown(
        '<span class="badge-der">der</span> Masculine &nbsp; '
        '<span class="badge-die">die</span> Feminine &nbsp; '
        '<span class="badge-das">das</span> Neuter',
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown(f"### ⭐ Saved Flashcards ({len(st.session_state.saved_phrases)})")
    if st.session_state.saved_phrases:
        for item in reversed(st.session_state.saved_phrases):
            st.markdown(
                f'<div class="flashcard"><b>EN:</b> {item["en"]}<br><b>DE:</b> <span style="color:#82E0AA;">{item["de"]}</span></div>',
                unsafe_allow_html=True
            )
        if st.button("Clear Saved Phrases", use_container_width=True):
            st.session_state.saved_phrases = []
            st.rerun()
    else:
        st.caption("Translate a phrase and click 'Save Flashcard' to build your deck.")

# --- MAIN INTERFACE ---
st.markdown('<div class="main-title">🇩🇪 DeutschBuddy</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Interactive English → German Translator & Language Companion</div>', unsafe_allow_html=True)

# Quick starter chips
st.caption("Try a quick example:")
ex_col1, ex_col2, ex_col3 = st.columns(3)
example_text = ""
if ex_col1.button("☕ Ordering coffee", use_container_width=True):
    example_text = "Could I please have a large coffee with oat milk?"
if ex_col2.button("🚉 Asking for directions", use_container_width=True):
    example_text = "Excuse me, how do I get to the central train station?"
if ex_col3.button("🤝 Meeting someone", use_container_width=True):
    example_text = "Nice to meet you! Where are you from?"

st.markdown("---")

col_in, col_out = st.columns(2, gap="large")

with col_in:
    st.markdown("#### 🇬🇧 English Input")
    english_input = st.text_area(
        label="Enter English text",
        value=example_text,
        height=160,
        placeholder="Type or paste English sentences here...",
        label_visibility="collapsed"
    )
    translate_btn = st.button("Translate to Deutsch ✨", type="primary", use_container_width=True)

with col_out:
    st.markdown(f"#### 🇩🇪 Deutsch Output ({tone})")
    if english_input.strip():
        if not gemini_key:
            st.warning("⚠️ Please enter your Gemini API key in the sidebar to run translations.")
        else:
            try:
                with st.spinner("Translating and analyzing grammar..."):
                    german_output, breakdown = translate_with_gemini(english_input, tone, gemini_key)
                
                # Display output card
                st.markdown(
                    f"""
                    <div class="output-card">
                        <div class="german-text">{german_output}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Audio & Action Row
                act_col1, act_col2 = st.columns([2, 1])
                with act_col1:
                    audio_bytes = generate_audio(german_output)
                    st.audio(audio_bytes, format="audio/mp3")
                with act_col2:
                    if st.button("⭐ Save Flashcard", use_container_width=True):
                        entry = {"en": english_input.strip(), "de": german_output}
                        if entry not in st.session_state.saved_phrases:
                            st.session_state.saved_phrases.append(entry)
                            st.toast("Saved to your study deck!", icon="✅")

                # Grammar & Noun Genders Expander
                with st.expander("🔍 Noun Genders & Grammar Breakdown", expanded=True):
                    st.markdown(breakdown)

            except Exception as e:
                st.error(f"Translation error: {e}")
    else:
        st.markdown(
            """
            <div class="output-card" style="opacity: 0.6;">
                <div class="german-text">Deine Übersetzung erscheint hier...</div>
                <small style="color: #A3E4D7;">(Your translation will appear here...)</small>
            </div>
            """,
            unsafe_allow_html=True
        )
