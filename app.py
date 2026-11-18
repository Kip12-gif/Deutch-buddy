import streamlit as st
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
import os
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
    /* Main headers */
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
    /* Translation output card */
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
    /* Gender Badges */
    .badge-der { background-color: #2980B9; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-die { background-color: #C0392B; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-das { background-color: #27AE60; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    
    /* Flashcard styling */
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
def translate_text(text: str) -> str:
    if not text.strip():
        return ""
    return GoogleTranslator(source="en", target="de").translate(text)

def generate_audio(german_text: str):
    tts = gTTS(text=german_text, lang="de", slow=False)
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp

def get_ai_breakdown(english_text: str, german_text: str, tone: str, api_key: str):
    """Uses Gemini to provide Du/Sie adjustments, noun genders, and grammar tips."""
    client = genai.Client(api_key=api_key)
    prompt = f"""
    You are a friendly German language tutor. Analyze this translation:
    English: "{english_text}"
    Standard German: "{german_text}"
    Requested Tone: {tone}

    Provide a concise, well-formatted breakdown:
    1. **Adjusted Translation ({tone}):** Rewrite the German specifically for {tone} context if needed.
    2. **Key Vocabulary & Noun Genders:** List important nouns with their article (der/die/das) and plural form.
    3. **Quick Grammar Tip:** One short, practical tip about word order, verb conjugation, or idioms used here.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text

# --- SIDEBAR: SETTINGS & SAVED FLASHCARDS ---
with st.sidebar:
    st.markdown("### ⚙️ Learning Settings")
    tone = st.radio(
        "Address Formality:",
        options=["Informal (Du)", "Formal (Sie)"],
        help="German distinguishes between casual ('du') and polite/professional ('Sie') speech."
    )
    
    st.markdown("---")
    st.markdown("### 🧠 AI Tutor (Optional)")
    gemini_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Add a free Google AI Studio key to unlock Du/Sie rewriting, noun gender tags, and grammar tips."
    )

    st.markdown("---")
    st.markdown("### 📚 Gender Color Guide")
    st.markdown(
        '<span class="badge-der">der</span> Masculine   '
        '<span class="badge-die">die</span> Feminine   '
        '<span class="badge-das">das</span> Neuter',
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown(f"### ⭐ Saved Flashcards ({len(st.session_state.saved_phrases)})")
    if st.session_state.saved_phrases:
        for idx, item in enumerate(reversed(st.session_state.saved_phrases)):
            st.markdown(
                f'<div class="flashcard"><b>EN:</b> {item["en"]}<br><b>DE:</b> <span style="color:#82E0AA;">{item["de"]}</span></div>',
                unsafe_allow_html=True
            )
        if st.button("Clear Saved Phrases", use_container_width=True):
            st.session_state.saved_phrases = []
            st.rerun()
    else:
        st.caption("Translate a phrase and click 'Save to Flashcards' to build your study deck.")

# --- MAIN INTERFACE ---
st.markdown('<div class="main-title">🇩🇪 DeutschBuddy</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Interactive English → German Translator & Language Companion</div>', unsafe_allow_html=True)

# Quick starter chips for learners
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

# Two-column layout: Input on Left, Output on Right
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
        try:
            german_output = translate_text(english_input)
            
            # Display stylized output card
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

            # AI Grammar & Nuance Drawer
            if gemini_key:
                with st.expander("🔍 Grammar, Noun Genders & Formality Breakdown", expanded=True):
                    with st.spinner("Analyzing German grammar..."):
                        breakdown = get_ai_breakdown(english_input, german_output, tone, gemini_key)
                        st.markdown(breakdown)
            else:
                st.info("💡 **Tip:** Paste a free Gemini API key in the sidebar to unlock *Du vs. Sie* rewriting, *der/die/das* gender tags, and grammar tips.")

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