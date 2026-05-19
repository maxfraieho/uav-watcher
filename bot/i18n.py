LANGS = ("uk", "en", "de", "fr", "pl")

STRINGS: dict[str, dict[str, str]] = {
    "uk": {
        "flag": "🇺🇦", "name": "Українська",
        "btn_shelter": "📍 Укриття поруч",
        "btn_threats": "⚠️ Загрози зараз",
        "btn_threat_types": "📋 Типи загроз",
        "btn_grounding": "🧘 Заземлення",
        "start_msg": (
            "👋 Привіт! Я *Sharon* — кризовий консультант.\n\n"
            "Надішли питання або скористайся кнопками нижче.\n\n"
            "📍 *Укриття поруч* — надішли геолокацію\n"
            "⚠️ *Загрози зараз* — поточна ситуація\n"
            "📋 *Типи загроз* — інструкції по кожному типу\n"
            "🧘 *Заземлення* — техніка при паніці"
        ),
        "shelter_geo_msg": (
            "📍 *Де ти зараз?*\n\n"
            "Надішли свою геолокацію — знайду найближчі укриття саме для тебе.\n\n"
            "*Як надіслати:*\n"
            "• Натисни 📎 (скрепка) → *Геолокація*\n"
            "• або: «+» → *Місцезнаходження* → *Поточне місцезнаходження*\n\n"
            "_Без точної геолокації покажу укриття лише від центру міста — вони можуть бути далеко від тебе._"
        ),
        "grounding_intro": "🧘 *Техніка заземлення — зупинись і читай повільно:*\n\nЦе допоможе тобі повернутись у теперішній момент.",
        "threats_err": "Не вдалось отримати дані.\nЕкстрені: 101 (ДСНС), 112",
        "chat_err": "Вибач, зараз не можу відповісти.\nЕкстрені: 101 (ДСНС), 112",
        "lang_chosen": "🇺🇦 Мову змінено на Українську.",
        "lang_prompt": "🌐 *Оберіть мову / Choose language:*",
        "detail_btn": "📡 Деталізуй з каналів",
        "detail_wait": "⏳ Збираю дані з каналів...",
        "detail_err": "Не вдалось отримати дані з каналів.",
        "threat_menu_title": "🛡 *Оберіть тип загрози:*",
        "llm_lang_instruction": "",
    },
    "en": {
        "flag": "🇬🇧", "name": "English",
        "btn_shelter": "📍 Shelter nearby",
        "btn_threats": "⚠️ Threats now",
        "btn_threat_types": "📋 Threat types",
        "btn_grounding": "🧘 Grounding",
        "start_msg": (
            "👋 Hi! I'm *Sharon* — a crisis safety assistant.\n\n"
            "Send a question or use the buttons below.\n\n"
            "📍 *Shelter nearby* — send your location\n"
            "⚠️ *Threats now* — current situation\n"
            "📋 *Threat types* — guides for each type\n"
            "🧘 *Grounding* — technique during panic"
        ),
        "shelter_geo_msg": (
            "📍 *Where are you now?*\n\n"
            "Send your location — I'll find the nearest shelters for you.\n\n"
            "*How to send:*\n"
            "• Tap 📎 → *Location*\n"
            "• or: «+» → *Location* → *Current location*\n\n"
            "_Without exact location I'll show shelters from the city center — they may be far from you._"
        ),
        "grounding_intro": "🧘 *Grounding technique — stop and read slowly:*\n\nThis will help you return to the present moment.",
        "threats_err": "Couldn't retrieve data.\nEmergency: 101 (DSNS), 112",
        "chat_err": "Sorry, I can't respond right now.\nEmergency: 101 (DSNS), 112",
        "lang_chosen": "🇬🇧 Language changed to English.",
        "lang_prompt": "🌐 *Choose language / Оберіть мову:*",
        "detail_btn": "📡 Detail from channels",
        "detail_wait": "⏳ Collecting data from channels...",
        "detail_err": "Couldn't retrieve data from channels.",
        "threat_menu_title": "🛡 *Choose threat type:*",
        "llm_lang_instruction": "\n\nIMPORTANT: Always respond in English regardless of the language the user writes in.",
    },
    "de": {
        "flag": "🇩🇪", "name": "Deutsch",
        "btn_shelter": "📍 Schutzraum",
        "btn_threats": "⚠️ Bedrohungen",
        "btn_threat_types": "📋 Bedrohungstypen",
        "btn_grounding": "🧘 Erdung",
        "start_msg": (
            "👋 Hallo! Ich bin *Sharon* — ein Krisenassistent.\n\n"
            "Sende eine Frage oder nutze die Schaltflächen unten.\n\n"
            "📍 *Schutzraum* — sende deinen Standort\n"
            "⚠️ *Bedrohungen* — aktuelle Situation\n"
            "📋 *Bedrohungstypen* — Anleitungen\n"
            "🧘 *Erdung* — Technik bei Panik"
        ),
        "shelter_geo_msg": (
            "📍 *Wo bist du gerade?*\n\n"
            "Sende deinen Standort — ich finde die nächsten Schutzräume.\n\n"
            "*Wie senden:*\n"
            "• Tippe 📎 → *Standort*\n"
            "• oder: «+» → *Standort* → *Aktueller Standort*\n\n"
            "_Ohne genauen Standort zeige ich Schutzräume vom Stadtzentrum — sie könnten weit weg sein._"
        ),
        "grounding_intro": "🧘 *Erdungstechnik — halte an und lies langsam:*\n\nDas hilft dir, in den Moment zurückzukehren.",
        "threats_err": "Daten konnten nicht abgerufen werden.\nNotfall: 101 (DSNS), 112",
        "chat_err": "Entschuldigung, ich kann gerade nicht antworten.\nNotfall: 101 (DSNS), 112",
        "lang_chosen": "🇩🇪 Sprache auf Deutsch geändert.",
        "lang_prompt": "🌐 *Sprache wählen / Оберіть мову:*",
        "detail_btn": "📡 Details aus Kanälen",
        "detail_wait": "⏳ Sammle Daten aus Kanälen...",
        "detail_err": "Daten aus Kanälen konnten nicht abgerufen werden.",
        "threat_menu_title": "🛡 *Bedrohungstyp wählen:*",
        "llm_lang_instruction": "\n\nWICHTIG: Antworte immer auf Deutsch, egal in welcher Sprache der Nutzer schreibt.",
    },
    "fr": {
        "flag": "🇫🇷", "name": "Français",
        "btn_shelter": "📍 Abri proche",
        "btn_threats": "⚠️ Menaces",
        "btn_threat_types": "📋 Types de menaces",
        "btn_grounding": "🧘 Ancrage",
        "start_msg": (
            "👋 Bonjour! Je suis *Sharon* — un assistant de crise.\n\n"
            "Envoyez une question ou utilisez les boutons ci-dessous.\n\n"
            "📍 *Abri proche* — envoyez votre localisation\n"
            "⚠️ *Menaces* — situation actuelle\n"
            "📋 *Types de menaces* — guides\n"
            "🧘 *Ancrage* — technique en cas de panique"
        ),
        "shelter_geo_msg": (
            "📍 *Où êtes-vous maintenant?*\n\n"
            "Envoyez votre localisation — je trouverai les abris les plus proches.\n\n"
            "*Comment envoyer:*\n"
            "• Appuyez sur 📎 → *Localisation*\n"
            "• ou: «+» → *Localisation* → *Position actuelle*\n\n"
            "_Sans localisation précise je montrerai les abris du centre-ville._"
        ),
        "grounding_intro": "🧘 *Technique d'ancrage — arrêtez-vous et lisez lentement:*\n\nCela vous aidera à revenir au moment présent.",
        "threats_err": "Impossible de récupérer les données.\nUrgence: 101 (DSNS), 112",
        "chat_err": "Désolé, je ne peux pas répondre maintenant.\nUrgence: 101 (DSNS), 112",
        "lang_chosen": "🇫🇷 Langue changée en Français.",
        "lang_prompt": "🌐 *Choisir la langue / Оберіть мову:*",
        "detail_btn": "📡 Détails des canaux",
        "detail_wait": "⏳ Collecte de données...",
        "detail_err": "Impossible de récupérer les données des canaux.",
        "threat_menu_title": "🛡 *Choisir le type de menace:*",
        "llm_lang_instruction": "\n\nIMPORTANT: Répondez toujours en français quelle que soit la langue de l'utilisateur.",
    },
    "pl": {
        "flag": "🇵🇱", "name": "Polski",
        "btn_shelter": "📍 Schronienie",
        "btn_threats": "⚠️ Zagrożenia",
        "btn_threat_types": "📋 Typy zagrożeń",
        "btn_grounding": "🧘 Uziemienie",
        "start_msg": (
            "👋 Cześć! Jestem *Sharon* — asystentem kryzysowym.\n\n"
            "Wyślij pytanie lub użyj przycisków poniżej.\n\n"
            "📍 *Schronienie* — wyślij lokalizację\n"
            "⚠️ *Zagrożenia* — aktualna sytuacja\n"
            "📋 *Typy zagrożeń* — instrukcje\n"
            "🧘 *Uziemienie* — technika podczas paniki"
        ),
        "shelter_geo_msg": (
            "📍 *Gdzie teraz jesteś?*\n\n"
            "Wyślij swoją lokalizację — znajdę najbliższe schronienia.\n\n"
            "*Jak wysłać:*\n"
            "• Naciśnij 📎 → *Lokalizacja*\n"
            "• lub: «+» → *Lokalizacja* → *Bieżąca lokalizacja*\n\n"
            "_Bez dokładnej lokalizacji pokażę schronienia z centrum miasta._"
        ),
        "grounding_intro": "🧘 *Technika uziemienia — zatrzymaj się i czytaj powoli:*\n\nTo pomoże ci wrócić do chwili obecnej.",
        "threats_err": "Nie udało się pobrać danych.\nNagłe: 101 (DSNS), 112",
        "chat_err": "Przepraszam, nie mogę teraz odpowiedzieć.\nNagłe: 101 (DSNS), 112",
        "lang_chosen": "🇵🇱 Język zmieniony na Polski.",
        "lang_prompt": "🌐 *Wybierz język / Оберіть мову:*",
        "detail_btn": "📡 Szczegóły z kanałów",
        "detail_wait": "⏳ Zbieram dane z kanałów...",
        "detail_err": "Nie udało się pobrać danych z kanałów.",
        "threat_menu_title": "🛡 *Wybierz typ zagrożenia:*",
        "llm_lang_instruction": "\n\nWAŻNE: Zawsze odpowiadaj po polsku niezależnie od języka użytkownika.",
    },
}

# Reverse lookup: button text → action key (works across all languages)
_BTN_TO_ACTION: dict[str, str] = {}
for _lang_key, _d in STRINGS.items():
    _BTN_TO_ACTION[_d["btn_shelter"]] = "shelter"
    _BTN_TO_ACTION[_d["btn_threats"]] = "threats"
    _BTN_TO_ACTION[_d["btn_threat_types"]] = "threat_types"
    _BTN_TO_ACTION[_d["btn_grounding"]] = "grounding"


def get(lang: str, key: str) -> str:
    return STRINGS.get(lang, STRINGS["uk"]).get(key, STRINGS["uk"].get(key, ""))


def action_for_button(text: str | None) -> str | None:
    """Return action key for button text in any language, or None."""
    return _BTN_TO_ACTION.get(text or "")


COMMANDS: dict[str, list[dict]] = {
    "uk": [
        {"command": "start",         "description": "▶️ Головне меню та типові ситуації"},
        {"command": "lang",          "description": "🌐 Змінити мову / Change language"},
        {"command": "setcity",       "description": "📍 Змінити місто"},
        {"command": "shelter",       "description": "🏠 Найближчі укриття"},
        {"command": "ok",            "description": "✅ Я в порядку"},
        {"command": "sos",           "description": "🆘 Потрібна допомога"},
        {"command": "checkin",       "description": "📍 Зберегти місцезнаходження"},
        {"command": "family_status", "description": "👨‍👩‍👧 Статус родини"},
        {"command": "family_create", "description": "Створити сімейну групу"},
        {"command": "family_join",   "description": "Приєднатись до групи"},
    ],
    "en": [
        {"command": "start",         "description": "▶️ Main menu & common situations"},
        {"command": "lang",          "description": "🌐 Change language / Змінити мову"},
        {"command": "setcity",       "description": "📍 Change city"},
        {"command": "shelter",       "description": "🏠 Nearest shelters"},
        {"command": "ok",            "description": "✅ I'm OK"},
        {"command": "sos",           "description": "🆘 I need help"},
        {"command": "checkin",       "description": "📍 Save my location"},
        {"command": "family_status", "description": "👨‍👩‍👧 Family status"},
        {"command": "family_create", "description": "Create family group"},
        {"command": "family_join",   "description": "Join family group"},
    ],
    "de": [
        {"command": "start",         "description": "▶️ Hauptmenü & typische Situationen"},
        {"command": "lang",          "description": "🌐 Sprache ändern / Change language"},
        {"command": "setcity",       "description": "📍 Stadt ändern"},
        {"command": "shelter",       "description": "🏠 Nächste Schutzräume"},
        {"command": "ok",            "description": "✅ Mir geht es gut"},
        {"command": "sos",           "description": "🆘 Ich brauche Hilfe"},
        {"command": "checkin",       "description": "📍 Standort speichern"},
        {"command": "family_status", "description": "👨‍👩‍👧 Familienstatus"},
        {"command": "family_create", "description": "Familiengruppe erstellen"},
        {"command": "family_join",   "description": "Familiengruppe beitreten"},
    ],
    "fr": [
        {"command": "start",         "description": "▶️ Menu principal & situations courantes"},
        {"command": "lang",          "description": "🌐 Changer la langue / Change language"},
        {"command": "setcity",       "description": "📍 Changer de ville"},
        {"command": "shelter",       "description": "🏠 Abris les plus proches"},
        {"command": "ok",            "description": "✅ Je vais bien"},
        {"command": "sos",           "description": "🆘 J'ai besoin d'aide"},
        {"command": "checkin",       "description": "📍 Enregistrer ma position"},
        {"command": "family_status", "description": "👨‍👩‍👧 Statut familial"},
        {"command": "family_create", "description": "Créer un groupe familial"},
        {"command": "family_join",   "description": "Rejoindre un groupe"},
    ],
    "pl": [
        {"command": "start",         "description": "▶️ Menu główne & typowe sytuacje"},
        {"command": "lang",          "description": "🌐 Zmień język / Change language"},
        {"command": "setcity",       "description": "📍 Zmień miasto"},
        {"command": "shelter",       "description": "🏠 Najbliższe schronienia"},
        {"command": "ok",            "description": "✅ Mam się dobrze"},
        {"command": "sos",           "description": "🆘 Potrzebuję pomocy"},
        {"command": "checkin",       "description": "📍 Zapisz moją lokalizację"},
        {"command": "family_status", "description": "👨‍👩‍👧 Status rodziny"},
        {"command": "family_create", "description": "Utwórz grupę rodzinną"},
        {"command": "family_join",   "description": "Dołącz do grupy"},
    ],
}
