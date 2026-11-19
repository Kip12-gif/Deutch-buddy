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
    .ref-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-left: 4px solid #82E0AA;
        padding: 12px 14px;
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
if "phrasebook_audio" not in st.session_state:
    st.session_state.phrasebook_audio = {}

DIALECT_MAP = {
    "Standard German (Germany)": "de-DE",
    "Austrian German": "de-AT",
    "Swiss German": "de-CH",
}

# --- LEARNER REFERENCE DATASETS (50+ ITEMS PER CATEGORY) ---
COMMON_NOUNS_50 = [
    ("der", "Apfel", "Äpfel", "apple"),
    ("das", "Brot", "Brote", "bread"),
    ("das", "Wasser", "Wässer", "water"),
    ("der", "Kaffee", "Kaffees", "coffee"),
    ("der", "Tee", "Tees", "tea"),
    ("die", "Milch", "—", "milk"),
    ("der", "Tisch", "Tische", "table"),
    ("der", "Stuhl", "Stühle", "chair"),
    ("das", "Haus", "Häuser", "house"),
    ("die", "Wohnung", "Wohnungen", "apartment"),
    ("das", "Zimmer", "Zimmer", "room"),
    ("die", "Küche", "Küchen", "kitchen"),
    ("das", "Bett", "Betten", "bed"),
    ("die", "Tür", "Türen", "door"),
    ("das", "Fenster", "Fenster", "window"),
    ("der", "Schlüssel", "Schlüssel", "key"),
    ("die", "Stadt", "Städte", "city"),
    ("das", "Land", "Länder", "country"),
    ("die", "Straße", "Straßen", "street"),
    ("der", "Platz", "Plätze", "square / place"),
    ("die", "Brücke", "Brücken", "bridge"),
    ("der", "Park", "Parks", "park"),
    ("die", "Karte", "Karten", "map / card"),
    ("der", "Zug", "Züge", "train"),
    ("der", "Bahnhof", "Bahnhöfe", "train station"),
    ("der", "Bus", "Busse", "bus"),
    ("das", "Auto", "Autos", "car"),
    ("das", "Fahrrad", "Fahrräder", "bicycle"),
    ("das", "Flugzeug", "Flugzeuge", "airplane"),
    ("der", "Flughafen", "Flughäfen", "airport"),
    ("die", "Fahrkarte", "Fahrkarten", "ticket"),
    ("das", "Hotel", "Hotels", "hotel"),
    ("das", "Restaurant", "Restaurants", "restaurant"),
    ("das", "Geschäft", "Geschäfte", "shop / store"),
    ("die", "Schule", "Schulen", "school"),
    ("die", "Universität", "Universitäten", "university"),
    ("das", "Büro", "Büros", "office"),
    ("die", "Arbeit", "Arbeiten", "work"),
    ("das", "Projekt", "Projekte", "project"),
    ("der", "Computer", "Computer", "computer"),
    ("das", "Telefon", "Telefone", "phone"),
    ("das", "Buch", "Bücher", "book"),
    ("die", "Zeitung", "Zeitungen", "newspaper"),
    ("das", "Geld", "Gelder", "money"),
    ("der", "Preis", "Preise", "price"),
    ("der", "Mann", "Männer", "man"),
    ("die", "Frau", "Frauen", "woman"),
    ("das", "Kind", "Kinder", "child"),
    ("die", "Familie", "Familien", "family"),
    ("der", "Freund", "Freunde", "friend"),
    ("die", "Zeit", "Zeiten", "time"),
    ("der", "Tag", "Tage", "day"),
]

COMMON_ADJECTIVES_50 = [
    ("gut", "besser", "am besten", "good"),
    ("schlecht", "schlechter", "am schlechtesten", "bad"),
    ("groß", "größer", "am größten", "big / tall"),
    ("klein", "kleiner", "am kleinsten", "small"),
    ("neu", "neuer", "am neuesten", "new"),
    ("alt", "älter", "am ältesten", "old"),
    ("jung", "jünger", "am jüngsten", "young"),
    ("schön", "schöner", "am schönsten", "beautiful / nice"),
    ("schnell", "schneller", "am schnellsten", "fast"),
    ("langsam", "langsamer", "am langsamsten", "slow"),
    ("lang", "länger", "am längsten", "long"),
    ("kurz", "kürzer", "am kürzesten", "short"),
    ("hoch", "höher", "am höchsten", "high / tall"),
    ("tief", "tiefer", "am tiefsten", "deep / low"),
    ("heiß", "heißer", "am heißesten", "hot"),
    ("warm", "wärmer", "am wärmsten", "warm"),
    ("kalt", "kälter", "am kältesten", "cold"),
    ("teuer", "teurer", "am teuersten", "expensive"),
    ("billig", "billiger", "am billigsten", "cheap / inexpensive"),
    ("frei", "freier", "am freiesten", "free / available"),
    ("offen", "offener", "am offensten", "open"),
    ("geschlossen", "geschlossener", "am geschlossensten", "closed"),
    ("einfach", "einfacher", "am einfachsten", "easy / simple"),
    ("schwierig", "schwieriger", "am schwierigsten", "difficult"),
    ("wichtig", "wichtiger", "am wichtigsten", "important"),
    ("richtig", "richtiger", "am richtigsten", "correct / right"),
    ("falsch", "falscher", "am falschesten", "wrong / false"),
    ("glücklich", "glücklicher", "am glücklichsten", "happy"),
    ("traurig", "trauriger", "am traurigsten", "sad"),
    ("müde", "müder", "am müdesten", "tired"),
    ("wach", "wacher", "am wachsten", "awake"),
    ("hungrig", "hungriger", "am hungrigsten", "hungry"),
    ("durstig", "durstiger", "am durstigsten", "thirsty"),
    ("gesund", "gesünder", "am gesündesten", "healthy"),
    ("krank", "kränker", "am kränksten", "sick / ill"),
    ("stark", "stärker", "am stärksten", "strong"),
    ("schwach", "schwächer", "am schwächsten", "weak"),
    ("laut", "lauter", "am lautesten", "loud"),
    ("leise", "leiser", "am leisesten", "quiet"),
    ("hell", "heller", "am hellsten", "bright / light"),
    ("dunkel", "dunkler", "am dunkelsten", "dark"),
    ("sauber", "sauberer", "am saubersten", "clean"),
    ("schmutzig", "schmutziger", "am schmutzigsten", "dirty"),
    ("voll", "voller", "am vollsten", "full"),
    ("leer", "leer", "am leersten", "empty"),
    ("freundlich", "freundlicher", "am freundlichsten", "friendly"),
    ("höflich", "höflicher", "am höflichsten", "polite"),
    ("klar", "klarer", "am klarsten", "clear"),
    ("sicher", "sicherer", "am sichersten", "safe / sure"),
    ("lecker", "leckerer", "am leckersten", "delicious / tasty"),
]

COMMON_PREPOSITIONS_50 = [
    ("mit", "Dative", "with", "Ich trinke Kaffee mit Milch."),
    ("nach", "Dative", "to / after", "Ich fahre nach Berlin."),
    ("aus", "Dative", "out of / from", "Sie kommt aus Kenia."),
    ("zu", "Dative", "to (person/place)", "Ich gehe zum Bahnhof."),
    ("bei", "Dative", "at / near / with", "Er wohnt bei seinen Eltern."),
    ("von", "Dative", "from / of", "Das Buch von meinem Freund."),
    ("seit", "Dative", "since / for (time)", "Ich lerne seit einem Jahr Deutsch."),
    ("außer", "Dative", "except / besides", "Alle außer mir sind da."),
    ("gegenüber", "Dative", "opposite", "Die Bank ist gegenüber dem Park."),
    ("durch", "Accusative", "through", "Wir gehen durch den Park."),
    ("für", "Accusative", "for", "Das Geschenk ist für dich."),
    ("gegen", "Accusative", "against / around (time)", "Wir treffen uns gegen acht Uhr."),
    ("ohne", "Accusative", "without", "Ich trinke Tee ohne Zucker."),
    ("um", "Accusative", "around / at (clock time)", "Der Zug kommt um neun Uhr."),
    ("bis", "Accusative", "until / up to", "Bis morgen!"),
    ("entlang", "Accusative / Dative", "along", "Gehen Sie die Straße entlang."),
    ("in", "Two-Way (Acc/Dat)", "in / into", "In der Stadt (Dat) / In die Stadt (Acc)."),
    ("an", "Two-Way (Acc/Dat)", "at / on (vertical)", "An der Tür (Dat) / An die Wand (Acc)."),
    ("auf", "Two-Way (Acc/Dat)", "on (horizontal surface)", "Auf dem Tisch (Dat) / Auf den Tisch (Acc)."),
    ("über", "Two-Way (Acc/Dat)", "over / above / about", "Über das Thema sprechen (Acc)."),
    ("unter", "Two-Way (Acc/Dat)", "under / below / among", "Unter dem Bett (Dat) / Unter das Bett (Acc)."),
    ("vor", "Two-Way (Acc/Dat)", "in front of / before", "Vor dem Haus (Dat) / Vor zehn Minuten (Dat)."),
    ("hinter", "Two-Way (Acc/Dat)", "behind", "Hinter dem Zug (Dat) / Hinter den Zug (Acc)."),
    ("neben", "Two-Way (Acc/Dat)", "next to", "Neben der Schule (Dat) / Neben die Lampe (Acc)."),
    ("zwischen", "Two-Way (Acc/Dat)", "between", "Zwischen uns (Dat) / Zwischen zwei Stühle (Acc)."),
    ("während", "Genitive", "during", "Während der Reise habe ich gelesen."),
    ("wegen", "Genitive", "because of", "Wegen des Regens bleiben wir hier."),
    ("trotz", "Genitive", "despite / in spite of", "Trotz des Lärms schlief er."),
    ("statt", "Genitive", "instead of", "Statt eines Autos fährt sie Rad."),
    ("anstatt", "Genitive", "instead of", "Anstatt Kaffee trinkt er Wasser."),
    ("innerhalb", "Genitive", "within / inside", "Innerhalb einer Woche."),
    ("außerhalb", "Genitive", "outside of", "Außerhalb der Stadt."),
    ("zum", "Dative contraction", "to the (zu + dem)", "Wir gehen zum Arzt."),
    ("zur", "Dative contraction", "to the (zu + der)", "Sie fährt zur Arbeit."),
    ("im", "Dative contraction", "in the (in + dem)", "Er ist im Büro."),
    ("ins", "Accusative contraction", "into the (in + das)", "Wir gehen ins Kino."),
    ("am", "Dative contraction", "at/on the (an + dem)", "Am Montag haben wir Zeit."),
    ("ans", "Accusative contraction", "to/on the (an + das)", "Ich denke ans Wochenende."),
    ("vom", "Dative contraction", "from the (von + dem)", "Vom Bahnhof sind es fünf Minuten."),
    ("beim", "Dative contraction", "at/while (bei + dem)", "Beim Essen sprechen wir Deutsch."),
    ("überm", "Accusative contraction", "over the (über + dem)", "Die Lampe hängt überm Tisch."),
    ("unterm", "Dative contraction", "under the (unter + dem)", "Der Ball liegt unterm Stuhl."),
    ("vorm", "Dative contraction", "in front of the (vor + dem)", "Wir warten vorm Hotel."),
    ("hinterm", "Dative contraction", "behind the (hinter + dem)", "Der Garten liegt hinterm Haus."),
    ("ab", "Dative / Accusative", "from / starting (time/place)", "Ab nächsten Monat."),
    ("samt", "Dative", "together with", "Samt Gepäck eingestiegen."),
    ("nahe", "Dative", "near / close to", "Nahe dem Zentrum."),
    ("gemäß", "Dative", "according to", "Den Regeln gemäß."),
    ("dank", "Genitive / Dative", "thanks to", "Dank deiner Hilfe."),
    ("zufolge", "Dative (after noun)", "according to", "Dem Bericht zufolge."),
]

CONJUGATED_VERBS_50 = [
    ("sein (to be)", "bin", "bist", "ist", "sind", "sind"),
    ("haben (to have)", "habe", "hast", "hat", "haben", "haben"),
    ("werden (to become)", "werde", "wirst", "wird", "werden", "werden"),
    ("gehen (to go)", "gehe", "gehst", "geht", "gehen", "gehen"),
    ("kommen (to come)", "komme", "kommst", "kommt", "kommen", "kommen"),
    ("machen (to do / make)", "mache", "machst", "macht", "machen", "machen"),
    ("sehen (to see)", "sehe", "siehst", "sieht", "sehen", "sehen"),
    ("hören (to hear / listen)", "höre", "hörst", "hört", "hören", "hören"),
    ("sprechen (to speak)", "spreche", "sprichst", "spricht", "sprechen", "sprechen"),
    ("sagen (to say)", "sage", "sagst", "sagt", "sagen", "sagen"),
    ("fragen (to ask)", "frage", "fragst", "fragt", "fragen", "fragen"),
    ("antworten (to answer)", "antworte", "antwortest", "antwortet", "antworten", "antworten"),
    ("verstehen (to understand)", "verstehe", "verstehst", "versteht", "verstehen", "verstehen"),
    ("wissen (to know facts)", "weiß", "weißt", "weiß", "wissen", "wissen"),
    ("kennen (to know people/places)", "kenne", "kennst", "kennt", "kennen", "kennen"),
    ("lernen (to learn)", "lerne", "lernst", "lernt", "lernen", "lernen"),
    ("lesen (to read)", "lese", "liest", "liest", "lesen", "lesen"),
    ("schreiben (to write)", "schreibe", "schreibst", "schreibt", "schreiben", "schreiben"),
    ("essen (to eat)", "esse", "isst", "isst", "essen", "essen"),
    ("trinken (to drink)", "trinke", "trinkst", "trinkt", "trinken", "trinken"),
    ("kaufen (to buy)", "kaufe", "kaufst", "kauft", "kaufen", "kaufen"),
    ("bezahlen (to pay)", "bezahle", "bezahlst", "bezahlt", "bezahlen", "bezahlen"),
    ("arbeiten (to work)", "arbeite", "arbeitest", "arbeitet", "arbeiten", "arbeiten"),
    ("wohnen (to live/reside)", "wohne", "wohnst", "wohnt", "wohnen", "wohnen"),
    ("leben (to live/be alive)", "lebe", "lebst", "lebt", "leben", "leben"),
    ("schlafen (to sleep)", "schlafe", "schläfst", "schläft", "schlafen", "schlafenn"),
    ("fahren (to drive/travel)", "fahre", "fährst", "fährt", "fahren", "fahren"),
    ("fliegen (to fly)", "fliege", "fliegst", "fliegt", "fliegen", "fliegen"),
    ("laufen (to run/walk)", "laufe", "läufst", "läuft", "laufen", "laufen"),
    ("finden (to find)", "finde", "findest", "findet", "finden", "finden"),
    ("geben (to give)", "gebe", "gibst", "gibt", "geben", "geben"),
    ("nehmen (to take)", "nehme", "nimmst", "nimmt", "nehmen", "nehmen"),
    ("helfen (to help)", "helfe", "hilfst", "hilft", "helfen", "helfen"),
    ("brauchen (to need)", "brauche", "brauchst", "braucht", "brauchen", "brauchen"),
    ("wollen (to want)", "will", "willst", "will", "wollen", "wollen"),
    ("können (can / be able)", "kann", "kannst", "kann", "können", "können"),
    ("müssen (must / have to)", "muss", "musst", "muss", "müssen", "müssen"),
    ("sollen (should / ought)", "soll", "sollst", "soll", "sollen", "sollen"),
    ("dürfen (may / be allowed)", "darf", "darfst", "darf", "dürfen", "dürfen"),
    ("mögen (to like)", "mag", "magst", "mag", "mögen", "mögen"),
    ("spielen (to play)", "spiele", "spielst", "spielt", "spielen", "spielen"),
    ("kochen (to cook)", "koche", "kochst", "kocht", "kochen", "kochen"),
    ("öffnen (to open)", "öffne", "öffnest", "öffnet", "öffnen", "öffnen"),
    ("schließen (to close)", "schließe", "schließt", "schließt", "schließen", "schließen"),
    ("beginnen (to begin)", "beginne", "beginnst", "beginnt", "beginnen", "beginnen"),
    ("warten (to wait)", "warte", "wartest", "wartet", "warten", "warten"),
    ("helfen", "helfe", "hilfst", "hilft", "helfen", "helfen"),
    ("zeigen (to show)", "zeige", "zeigst", "zeigt", "zeigen", "zeigen"),
    ("suchen (to search / look for)", "suche", "suchst", "sucht", "suchen", "suchen"),
    ("treffen (to meet)", "treffe", "triffst", "trifft", "treffen", "treffen"),
]

COMMON_PRONOUNS_50 = [
    ("ich", "Personal (Nom)", "I", "Ich lerne Deutsch."),
    ("mich", "Personal (Acc)", "me", "Sie sieht mich."),
    ("mir", "Personal (Dat)", "me / to me", "Hilf mir bitte."),
    ("du", "Personal (Nom)", "you (informal sg.)", "Woher kommst du?"),
    ("dich", "Personal (Acc)", "you (informal sg.)", "Ich verstehe dich."),
    ("dir", "Personal (Dat)", "you / to you (inf.)", "Wie geht es dir?"),
    ("er", "Personal (Nom)", "he", "Er arbeitet hier."),
    ("ihn", "Personal (Acc)", "him", "Ich kenne ihn."),
    ("ihm", "Personal (Dat)", "him / to him", "Ich gebe ihm das Buch."),
    ("sie (sg.)", "Personal (Nom)", "she", "Sie kommt aus Berlin."),
    ("sie (sg. Acc)", "Personal (Acc)", "her", "Ich sehe sie."),
    ("ihr (sg. Dat)", "Personal (Dat)", "her / to her", "Ich antworte ihr."),
    ("es", "Personal (Nom/Acc)", "it", "Es regnet heute."),
    ("ihm (neut. Dat)", "Personal (Dat)", "it / to it", "Das passt ihm gut."),
    ("wir", "Personal (Nom)", "we", "Wir reisen morgen."),
    ("uns", "Personal (Acc/Dat)", "us / to us", "Besuch uns bald!"),
    ("ihr (pl.)", "Personal (Nom)", "you all (informal pl.)", "Habt ihr Zeit?"),
    ("euch", "Personal (Acc/Dat)", "you all / to you all", "Ich danke euch."),
    ("sie (pl.)", "Personal (Nom)", "they", "Sie lernen zusammen."),
    ("sie (pl. Acc)", "Personal (Acc)", "them", "Ich rufe sie an."),
    ("ihnen (pl. Dat)", "Personal (Dat)", "them / to them", "Ich erkläre ihnen das."),
    ("Sie (formal)", "Personal (Nom/Acc)", "you (formal)", "Wie heißen Sie?"),
    ("Ihnen (formal)", "Personal (Dat)", "you / to you (formal)", "Wie geht es Ihnen?"),
    ("mein / meine", "Possessive", "my", "Das ist mein Freund."),
    ("dein / deine", "Possessive", "your (informal sg.)", "Wo ist deine Tasche?"),
    ("sein / seine", "Possessive", "his / its", "Er sucht sein Handy."),
    ("ihr / ihre", "Possessive", "her / their", "Sie liest ihr Buch."),
    ("unser / unsere", "Possessive", "our", "Unser Zug fährt gleich."),
    ("euer / eure", "Possessive", "your (informal pl.)", "Euer Haus ist groß."),
    ("Ihr / Ihre", "Possessive (Formal)", "your (formal)", "Ist das Ihr Kaffee?"),
    ("wer", "Interrogative (Nom)", "who", "Wer kommt mit?"),
    ("wen", "Interrogative (Acc)", "whom", "Wen triffst du heute?"),
    ("wem", "Interrogative (Dat)", "to whom", "Wem gehört das?"),
    ("wessen", "Interrogative (Gen)", "whose", "Wessen Buch ist das?"),
    ("was", "Interrogative", "what", "Was machst du?"),
    ("welcher / welche / welches", "Interrogative", "which", "Welcher Zug ist das?"),
    ("dieser / diese / dieses", "Demonstrative", "this", "Dieses Ticket ist gültig."),
    ("jener / jene / jenes", "Demonstrative", "that (distant)", "Jenes Gebäude ist alt."),
    ("der / die / das (dem.)", "Demonstrative", "that one / the", "Das ist richtig."),
    ("man", "Indefinite", "one / people / they", "Hier spricht man Deutsch."),
    ("jemand", "Indefinite", "someone", "Ist jemand da?"),
    ("niemand", "Indefinite", "no one", "Niemand hat angerufen."),
    ("etwas", "Indefinite", "something", "Möchtest du etwas trinken?"),
    ("nichts", "Indefinite", "nothing", "Ich habe nichts gehört."),
    ("alles", "Indefinite", "everything", "Alles ist bereit."),
    ("jeder / jede / jedes", "Indefinite", "each / every", "Jeder Tag ist neu."),
    ("einige / manche", "Indefinite", "some / several", "Einige Gäste sind da."),
    ("alle", "Indefinite", "all / everyone", "Alle sind willkommen."),
    ("sich", "Reflexive", "himself/herself/themselves", "Er wäscht sich."),
    ("einander", "Reciprocal", "each other", "Wir helfen einander."),
]


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

# --- TABS: TRANSLATOR, STARTER PHRASEBOOK & GRAMMAR REFERENCE ---
tab_translate, tab_phrasebook, tab_reference = st.tabs(
    ["Translator & Lookup", "Starter Phrasebook", "Grammar & Vocab Bar"]
)

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
    st.markdown("#### Browse & Search Curated Offline Phrases")
    if not PHRASES_DATA:
        st.warning("No phrases.json file was detected in your repository.")
    else:
        categories = ["All Categories"] + sorted(
            {p.get("category", "General") for p in PHRASES_DATA}
        )

        flt_col1, flt_col2 = st.columns([2, 1])
        with flt_col1:
            search_query = st.text_input(
                "Search keywords (English, German, category, or note)",
                placeholder="e.g., coffee, train, Bahnhof, ticket, weekend...",
            )
        with flt_col2:
            selected_cat = st.selectbox("Filter by Category", options=categories)

        kw = search_query.strip().lower()
        filtered = []
        for p in PHRASES_DATA:
            cat_match = (
                selected_cat == "All Categories"
                or p.get("category", "General") == selected_cat
            )
            searchable_blob = " ".join(
                [
                    str(p.get("en", "")),
                    str(p.get("du", "")),
                    str(p.get("sie", "")),
                    str(p.get("category", "")),
                    str(p.get("note", "")),
                ]
            ).lower()
            kw_match = not kw or (kw in searchable_blob)
            if cat_match and kw_match:
                filtered.append(p)

        st.caption(f"Showing **{len(filtered)}** of **{len(PHRASES_DATA)}** phrases")

        if not filtered:
            st.info("No matching phrases found. Try clearing your keyword search or switching categories.")
        else:
            for idx, item in enumerate(filtered):
                german_line = (
                    item.get("du") if tone == "Informal (Du)" else item.get("sie")
                ) or (item.get("du") or item.get("sie") or "")
                phrase_key = f"{item.get('id', idx)}_{tone}_{'slow' if slow_audio else 'fast'}"

                st.markdown(
                    f"""
                    <div class="output-card">
                        <span class="source-pill">{item.get("category", "General")} • {tone}</span>
                        <div style="color:#A3E4D7; font-size:0.95rem; margin-bottom:4px;">🇬🇧 {item.get("en", "")}</div>
                        <div class="german-text">🇩🇪 {german_line}</div>
                        <div class="meta-note">💡 {item.get("note", "")}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                aud_btn_col, aud_player_col = st.columns([1, 3])
                with aud_btn_col:
                    if st.button(
                        "🔊 Listen",
                        key=f"play_btn_{phrase_key}",
                        use_container_width=True,
                    ):
                        try:
                            with st.spinner("Generating audio..."):
                                st.session_state.phrasebook_audio[phrase_key] = (
                                    generate_audio(german_line, slow_mode=slow_audio)
                                )
                        except Exception as audio_err:
                            st.caption(f"Audio unavailable: {audio_err}")

                with aud_player_col:
                    if phrase_key in st.session_state.phrasebook_audio:
                        st.audio(
                            st.session_state.phrasebook_audio[phrase_key],
                            format="audio/mp3",
                        )

with tab_reference:
    st.markdown("#### AI Study & Grammar Reference Bar (50+ Entries per Category)")
    st.caption(
        "Quick-scan reference for nouns, adjectives, prepositions, conjugated verbs, and pronouns."
    )

    ref_filter = st.text_input(
        "Filter reference tables by keyword",
        placeholder="Type a German or English word, case (Dative, Accusative), or pronoun...",
        key="ref_search_box",
    ).strip().lower()

    part_of_speech = st.radio(
        "Select Word Class",
        options=[
            f"Nouns ({len(COMMON_NOUNS_50)})",
            f"Adjectives ({len(COMMON_ADJECTIVES_50)})",
            f"Prepositions ({len(COMMON_PREPOSITIONS_50)})",
            f"Conjugated Verbs ({len(CONJUGATED_VERBS_50)})",
            f"Pronouns ({len(COMMON_PRONOUNS_50)})",
        ],
        horizontal=True,
    )

    if part_of_speech.startswith("Nouns"):
        rows = [
            {"Article": art, "Noun": noun, "Plural": plur, "English": en}
            for art, noun, plur, en in COMMON_NOUNS_50
            if not ref_filter
            or ref_filter in f"{art} {noun} {plur} {en}".lower()
        ]
        st.markdown(f"**Showing {len(rows)} common nouns**")
        st.dataframe(rows, use_container_width=True, hide_index=True)

    elif part_of_speech.startswith("Adjectives"):
        rows = [
            {
                "Base": base,
                "Comparative": comp,
                "Superlative": sup,
                "English": en,
            }
            for base, comp, sup, en in COMMON_ADJECTIVES_50
            if not ref_filter
            or ref_filter in f"{base} {comp} {sup} {en}".lower()
        ]
        st.markdown(f"**Showing {len(rows)} common adjectives**")
        st.dataframe(rows, use_container_width=True, hide_index=True)

    elif part_of_speech.startswith("Prepositions"):
        rows = [
            {
                "Preposition": prep,
                "Case": case_rule,
                "English": en,
                "Example": example,
            }
            for prep, case_rule, en, example in COMMON_PREPOSITIONS_50
            if not ref_filter
            or ref_filter in f"{prep} {case_rule} {en} {example}".lower()
        ]
        st.markdown(f"**Showing {len(rows)} common prepositions**")
        st.dataframe(rows, use_container_width=True, hide_index=True)

    elif part_of_speech.startswith("Conjugated Verbs"):
        rows = [
            {
                "Infinitive": inf,
                "ich": ich_f,
                "du": du_f,
                "er/sie/es": er_f,
                "wir": wir_f,
                "Sie": sie_f,
            }
            for inf, ich_f, du_f, er_f, wir_f, sie_f in CONJUGATED_VERBS_50
            if not ref_filter
            or ref_filter
            in f"{inf} {ich_f} {du_f} {er_f} {wir_f} {sie_f}".lower()
        ]
        st.markdown(f"**Showing {len(rows)} conjugated verbs (present tense)**")
        st.dataframe(rows, use_container_width=True, hide_index=True)

    else:
        rows = [
            {
                "Pronoun": pron,
                "Type / Case": p_type,
                "English": en,
                "Example": example,
            }
            for pron, p_type, en, example in COMMON_PRONOUNS_50
            if not ref_filter
            or ref_filter in f"{pron} {p_type} {en} {example}".lower()
        ]
        st.markdown(f"**Showing {len(rows)} common pronouns**")
        st.dataframe(rows, use_container_width=True, hide_index=True)
