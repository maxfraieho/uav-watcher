"""
Crisis response templates for Sharon chatbot.
Sources: DSNS, WHO, IFRC, Israeli HFC model.
"""

# ── Ukrainian originals (kept for backward compat) ──────────────────────────

TEMPLATES = {
    "uav": {
        "title": "🚁 ЗАГРОЗА БПЛА / ДРОН-КАМІКАДЗЕ",
        "text": (
            "🚁 *ЗАГРОЗА БПЛА — ДІЙ ЗАРАЗ*\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Відійди від вікон — ляж на підлогу\n"
            "• Вимкни світло, закрий штори (перекриває оптику)\n"
            "• НЕ виходь надвір — дрон відстежує рух\n"
            "• Телефон на беззвучний, але НЕ вимикай\n\n"
            "🏠 *УКРИТТЯ (правило двох стін):*\n"
            "Ванна кімната або коридор > підвал\n"
            "НЕ ховайся під сходами (ризик обвалу)\n\n"
            "💥 *ПІСЛЯ ВИБУХУ В РАДІУСІ 500м:*\n"
            "• Зачини вікна (хімічна загроза)\n"
            "• Не виходь 15 хв (можлива друга хвиля)\n"
            "• Зателефонуй: 101 або 112"
        )
    },
    "ballistic": {
        "title": "🚀 БАЛІСТИЧНА РАКЕТА / ISKANDER",
        "text": (
            "🚀 *БАЛІСТИЧНА ЗАГРОЗА — СЕКУНДИ ВИРІШУЮТЬ*\n\n"
            "⚡ Час: 2–4 хвилини до удару\n\n"
            "✅ *ЯКЩО Є ЧАС:*\n"
            "Підвал або 1-й поверх, несучі стіни\n\n"
            "✅ *ЯКЩО НЕ ВСТИГ:*\n"
            "• Ляж у будь-яке заглиблення (канава, підземний перехід)\n"
            "• Відкрий рот (від вибухової хвилі)\n"
            "• Прикрий потилицю руками\n"
            "• Відвернись від напрямку загрози\n\n"
            "📵 НЕ знімай відео — йди в укриття"
        )
    },
    "cruise": {
        "title": "✈️ КРИЛАТА РАКЕТА / KALIBR",
        "text": (
            "✈️ *КРИЛАТА РАКЕТА — УКРИЙСЯ*\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Підземний паркінг або підвал — мета №1\n"
            "• Від вікон якомога далі\n"
            "• Не стій у відкритих місцях\n\n"
            "⚠️ Kalibr летить на малій висоті — попередження може бути коротким\n\n"
            "🔇 Вимкни газ, відкрий вікно в іншій кімнаті (від вибухової хвилі)\n\n"
            "📞 Після відбою: 101 (ДСНС), 112"
        )
    },
    "fab": {
        "title": "💣 АВІАБОМБА FAB / Планер",
        "text": (
            "💣 *FAB АВІАБОМБА — МАКСИМАЛЬНА ЗАГРОЗА*\n\n"
            "‼️ Правило двох стін НЕ ПРАЦЮЄ\n"
            "‼️ Потрібен ГЛИБОКИЙ підвал або багаторівневе бомбосховище\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Глибоке бомбосховище / метро / підземний паркінг\n"
            "• НЕ залишайся в квартирі — навіть на 1-му поверсі\n"
            "• Якщо немає укриття — відійди від будівель щонайменше 50м\n"
            "• Ляж у ямку/канаву, прикрий голову\n\n"
            "📞 112 або 101 — після удару"
        )
    },
    "chemical": {
        "title": "☣️ ХІМІЧНА / ТОКСИЧНА ЗАГРОЗА",
        "text": (
            "☣️ *ХІМІЧНА ЗАГРОЗА — ГЕРМЕТИЗУЙ ПРИМІЩЕННЯ*\n\n"
            "🔴 Ознаки: незвичний запах, димова хмара, симптоми у людей\n\n"
            "✅ *НЕГАЙНО:*\n"
            "• Закрий ВСІ вікна і двері ГЕРМЕТИЧНО\n"
            "• Змочи тканину — прикрий рот і ніс\n"
            "• Піднімись вище (більшість газів важчі за повітря)\n"
            "• Заклей щілини скотчем якщо є\n\n"
            "🚫 *НЕ виходь без захисту*\n\n"
            "✅ *Якщо ти надворі:*\n"
            "• Тримайся з навітряного боку\n"
            "• Знімай одяг, рясно промивай шкіру водою\n\n"
            "📞 101 — одразу"
        )
    },
    "rubble": {
        "title": "🆘 ПІД ЗАВАЛАМИ / БУДИНОК ЗРУЙНОВАНО",
        "text": (
            "🆘 *ПІД ЗАВАЛАМИ — ЩО РОБИТИ*\n\n"
            "📱 *ЯКЩО ТИ ПІД ЗАВАЛАМИ:*\n"
            "• Натисни кнопку SOS нижче — надсилається GPS\n"
            "• Стукай по трубах або бетону КОЖНІ 30 СЕК\n"
            "• Прикрий рот тканиною від пилу\n"
            "• Дихай спокійно — економ кисень\n"
            "• НЕ кричи постійно — втратиш сили\n\n"
            "👥 *ЯКЩО ШУКАЄШ ЛЮДИНУ:*\n"
            "• Зателефонуй 101 (ДСНС) — ПЕРШОЧЕРГОВО\n"
            "• Слухай кожні 2 хвилини: стукіт, голос\n"
            "• НЕ рухай великі уламки самостійно\n"
            "• Перевір останнє місце через бота (кнопка нижче)"
        )
    },
    "allclear": {
        "title": "✅ ВІДБІЙ ТРИВОГИ",
        "text": (
            "✅ *ВІДБІЙ — НЕБЕЗПЕКА МИНУЛА*\n\n"
            "Перш ніж виходити:\n"
            "• Зачекай 5–10 хвилин після офіційного відбою\n"
            "• Оглянь вулицю через вікно перед виходом\n"
            "• Не торкайся невідомих предметів на вулиці\n\n"
            "💬 Повідом рідних що ти в безпеці (/status)\n\n"
            "📊 Перевір статус сім'ї: /family_status"
        )
    }
}

THREAT_KEYBOARD = [
    [{"text": "🚁 БПЛА/Дрон", "callback_data": "crisis_uav"},
     {"text": "🚀 Балістика", "callback_data": "crisis_ballistic"}],
    [{"text": "✈️ Крилата ракета", "callback_data": "crisis_cruise"},
     {"text": "💣 FAB бомба", "callback_data": "crisis_fab"}],
    [{"text": "☣️ Хімічна загроза", "callback_data": "crisis_chemical"},
     {"text": "🆘 Під завалами", "callback_data": "crisis_rubble"}],
    [{"text": "✅ Відбій", "callback_data": "crisis_allclear"}]
]

GROUNDING_STEPS = [
    "🟢 Крок 1/5 — Назви 5 речей які ти БАЧИШ зараз",
    "🟢 Крок 2/5 — Торкнись 4 різних поверхні поруч з тобою",
    "🟢 Крок 3/5 — Прислухайся — назви 3 звуки які чуєш",
    "🟢 Крок 4/5 — Відчуй 2 запахи або текстури",
    "🟢 Крок 5/5 — Зроби 1 глибокий вдих... і повільний видих.\n\n✅ Ти тут. Ти в безпеці. Продовжуй дихати рівно."
]


# ── Multilingual keyboard ───────────────────────────────────────────────────

_KEYBOARD_CALLBACKS = [
    ["crisis_uav",      "crisis_ballistic"],
    ["crisis_cruise",   "crisis_fab"],
    ["crisis_chemical", "crisis_rubble"],
    ["crisis_allclear"],
]

_KEYBOARD_LABELS: dict[str, list[list[str]]] = {
    "uk": [
        ["🚁 БПЛА/Дрон",       "🚀 Балістика"],
        ["✈️ Крилата ракета",  "💣 FAB бомба"],
        ["☣️ Хімічна загроза", "🆘 Під завалами"],
        ["✅ Відбій"],
    ],
    "en": [
        ["🚁 UAV/Drone",        "🚀 Ballistic"],
        ["✈️ Cruise missile",   "💣 FAB bomb"],
        ["☣️ Chemical threat",  "🆘 Under rubble"],
        ["✅ All clear"],
    ],
    "de": [
        ["🚁 UAV/Drohne",          "🚀 Ballistische Rakete"],
        ["✈️ Marschflugkörper",    "💣 FAB-Bombe"],
        ["☣️ Chemische Gefahr",    "🆘 Unter Trümmern"],
        ["✅ Entwarnung"],
    ],
    "fr": [
        ["🚁 UAV/Drone",           "🚀 Missile balistique"],
        ["✈️ Missile de croisière","💣 Bombe FAB"],
        ["☣️ Menace chimique",     "🆘 Sous les décombres"],
        ["✅ Fin d'alerte"],
    ],
    "pl": [
        ["🚁 UAV/Dron",            "🚀 Pocisk balistyczny"],
        ["✈️ Pocisk manewrujący",  "💣 Bomba FAB"],
        ["☣️ Zagrożenie chemiczne","🆘 Pod gruzami"],
        ["✅ Odwołanie alarmu"],
    ],
}


def get_threat_keyboard(lang: str = "uk") -> list:
    """Return THREAT_KEYBOARD structure with localized button text."""
    labels = _KEYBOARD_LABELS.get(lang, _KEYBOARD_LABELS["uk"])
    result = []
    for i, callbacks in enumerate(_KEYBOARD_CALLBACKS):
        row_labels = labels[i] if i < len(labels) else []
        row = []
        for j, cb in enumerate(callbacks):
            text = row_labels[j] if j < len(row_labels) else cb
            row.append({"text": text, "callback_data": cb})
        result.append(row)
    return result


# ── Multilingual grounding steps ────────────────────────────────────────────

_GROUNDING_STEPS_I18N: dict[str, list[str]] = {
    "uk": [
        "🟢 Крок 1/5 — Назви 5 речей які ти БАЧИШ зараз",
        "🟢 Крок 2/5 — Торкнись 4 різних поверхні поруч з тобою",
        "🟢 Крок 3/5 — Прислухайся — назви 3 звуки які чуєш",
        "🟢 Крок 4/5 — Відчуй 2 запахи або текстури",
        "🟢 Крок 5/5 — Зроби 1 глибокий вдих... і повільний видих.\n\n✅ Ти тут. Ти в безпеці. Продовжуй дихати рівно.",
    ],
    "en": [
        "🟢 Step 1/5 — Name 5 things you SEE right now",
        "🟢 Step 2/5 — Touch 4 different surfaces near you",
        "🟢 Step 3/5 — Listen — name 3 sounds you can hear",
        "🟢 Step 4/5 — Notice 2 smells or textures",
        "🟢 Step 5/5 — Take 1 deep breath... and exhale slowly.\n\n✅ You are here. You are safe. Keep breathing steadily.",
    ],
    "de": [
        "🟢 Schritt 1/5 — Nenne 5 Dinge, die du gerade SIEHST",
        "🟢 Schritt 2/5 — Berühre 4 verschiedene Oberflächen in deiner Nähe",
        "🟢 Schritt 3/5 — Höre hin — nenne 3 Geräusche, die du hörst",
        "🟢 Schritt 4/5 — Nimm 2 Gerüche oder Texturen wahr",
        "🟢 Schritt 5/5 — Atme einmal tief ein... und langsam aus.\n\n✅ Du bist hier. Du bist sicher. Atme gleichmäßig weiter.",
    ],
    "fr": [
        "🟢 Étape 1/5 — Nomme 5 choses que tu VOIS en ce moment",
        "🟢 Étape 2/5 — Touche 4 surfaces différentes près de toi",
        "🟢 Étape 3/5 — Écoute — nomme 3 sons que tu entends",
        "🟢 Étape 4/5 — Perçois 2 odeurs ou textures",
        "🟢 Étape 5/5 — Prends 1 grande inspiration... et expire lentement.\n\n✅ Tu es ici. Tu es en sécurité. Continue à respirer régulièrement.",
    ],
    "pl": [
        "🟢 Krok 1/5 — Nazwij 5 rzeczy, które teraz WIDZISZ",
        "🟢 Krok 2/5 — Dotknij 4 różnych powierzchni w pobliżu",
        "🟢 Krok 3/5 — Słuchaj — nazwij 3 dźwięki, które słyszysz",
        "🟢 Krok 4/5 — Poczuj 2 zapachy lub faktury",
        "🟢 Krok 5/5 — Weź 1 głęboki oddech... i powoli wydech.\n\n✅ Jesteś tutaj. Jesteś bezpieczny. Oddychaj równomiernie.",
    ],
}


def get_grounding_steps(lang: str = "uk") -> list[str]:
    return _GROUNDING_STEPS_I18N.get(lang, _GROUNDING_STEPS_I18N["uk"])


# ── Multilingual threat templates ───────────────────────────────────────────

_TEMPLATES_I18N: dict[str, dict[str, str]] = {
    "uk": {k: v["text"] for k, v in TEMPLATES.items()},
    "en": {
        "uav": (
            "🚁 *UAV THREAT — ACT NOW*\n\n"
            "✅ *IMMEDIATELY:*\n"
            "• Move away from windows — lie on the floor\n"
            "• Turn off lights, close curtains (blocks drone optics)\n"
            "• DO NOT go outside — drone tracks movement\n"
            "• Phone on silent, but DO NOT turn off\n\n"
            "🏠 *SHELTER (two-wall rule):*\n"
            "Bathroom or corridor > basement\n"
            "DO NOT hide under stairs (collapse risk)\n\n"
            "💥 *AFTER EXPLOSION WITHIN 500m:*\n"
            "• Close windows (chemical threat)\n"
            "• Don't go outside for 15 min (possible second wave)\n"
            "• Call: 101 or 112"
        ),
        "ballistic": (
            "🚀 *BALLISTIC THREAT — SECONDS MATTER*\n\n"
            "⚡ Time: 2–4 minutes to impact\n\n"
            "✅ *IF YOU HAVE TIME:*\n"
            "Basement or ground floor, load-bearing walls\n\n"
            "✅ *IF CAUGHT OUTSIDE:*\n"
            "• Lie in any depression (ditch, underpass)\n"
            "• Open your mouth (from blast wave)\n"
            "• Cover the back of your head with hands\n"
            "• Turn away from the direction of the threat\n\n"
            "📵 DO NOT film — take cover"
        ),
        "cruise": (
            "✈️ *CRUISE MISSILE — TAKE COVER*\n\n"
            "✅ *IMMEDIATELY:*\n"
            "• Underground parking or basement — priority #1\n"
            "• Stay as far from windows as possible\n"
            "• Don't stand in open spaces\n\n"
            "⚠️ Kalibr flies at low altitude — warning may be very short\n\n"
            "🔇 Turn off gas, open a window in another room (from blast wave)\n\n"
            "📞 After all-clear: 101 (DSNS), 112"
        ),
        "fab": (
            "💣 *FAB BOMB — MAXIMUM THREAT*\n\n"
            "‼️ Two-wall rule DOES NOT WORK\n"
            "‼️ Need DEEP basement or multi-level bomb shelter\n\n"
            "✅ *IMMEDIATELY:*\n"
            "• Deep bomb shelter / metro / underground parking\n"
            "• DO NOT stay in apartment — even on ground floor\n"
            "• If no shelter — move at least 50m away from buildings\n"
            "• Lie in a pit/ditch, cover your head\n\n"
            "📞 112 or 101 — after impact"
        ),
        "chemical": (
            "☣️ *CHEMICAL THREAT — SEAL THE ROOM*\n\n"
            "🔴 Signs: unusual smell, smoke cloud, symptoms in people\n\n"
            "✅ *IMMEDIATELY:*\n"
            "• Close ALL windows and doors TIGHTLY\n"
            "• Wet a cloth — cover mouth and nose\n"
            "• Move higher (most gases are heavier than air)\n"
            "• Seal gaps with tape if available\n\n"
            "🚫 *DO NOT go outside without protection*\n\n"
            "✅ *If you're outside:*\n"
            "• Stay on the upwind side\n"
            "• Remove clothing, rinse skin thoroughly with water\n\n"
            "📞 101 — immediately"
        ),
        "rubble": (
            "🆘 *UNDER RUBBLE — WHAT TO DO*\n\n"
            "📱 *IF YOU'RE UNDER RUBBLE:*\n"
            "• Press the SOS button below — sends GPS\n"
            "• Knock on pipes or concrete EVERY 30 SEC\n"
            "• Cover your mouth with cloth against dust\n"
            "• Breathe calmly — conserve oxygen\n"
            "• DON'T shout constantly — you'll lose strength\n\n"
            "👥 *IF YOU'RE SEARCHING FOR SOMEONE:*\n"
            "• Call 101 (DSNS) — FIRST PRIORITY\n"
            "• Listen every 2 minutes: knocking, voice\n"
            "• DO NOT move large debris alone\n"
            "• Check last known location via bot (button below)"
        ),
        "allclear": (
            "✅ *ALL CLEAR — DANGER HAS PASSED*\n\n"
            "Before going outside:\n"
            "• Wait 5–10 minutes after the official all-clear\n"
            "• Check the street through the window before leaving\n"
            "• Don't touch unknown objects on the street\n\n"
            "💬 Let family know you're safe (/status)\n\n"
            "📊 Check family status: /family_status"
        ),
    },
    "de": {
        "uav": (
            "🚁 *DROHNENBEDROHUNG — JETZT HANDELN*\n\n"
            "✅ *SOFORT:*\n"
            "• Weg von Fenstern — auf den Boden legen\n"
            "• Licht aus, Vorhänge schließen (blockiert Drohnenoptik)\n"
            "• NICHT nach draußen — Drohne verfolgt Bewegungen\n"
            "• Handy auf lautlos, aber NICHT ausschalten\n\n"
            "🏠 *SCHUTZ (Zwei-Wände-Regel):*\n"
            "Bad oder Korridor > Keller\n"
            "NICHT unter der Treppe verstecken (Einsturzgefahr)\n\n"
            "💥 *NACH EXPLOSION IM RADIUS 500m:*\n"
            "• Fenster schließen (chemische Gefahr)\n"
            "• 15 Min nicht rausgehen (mögliche zweite Welle)\n"
            "• Rufe an: 101 oder 112"
        ),
        "ballistic": (
            "🚀 *BALLISTISCHE BEDROHUNG — SEKUNDEN ENTSCHEIDEN*\n\n"
            "⚡ Zeit: 2–4 Minuten bis zum Einschlag\n\n"
            "✅ *WENN DU ZEIT HAST:*\n"
            "Keller oder Erdgeschoss, tragende Wände\n\n"
            "✅ *WENN KEINE ZEIT:*\n"
            "• Leg dich in jede Vertiefung (Graben, Unterführung)\n"
            "• Öffne den Mund (wegen der Druckwelle)\n"
            "• Bedecke den Hinterkopf mit den Händen\n"
            "• Wende dich von der Bedrohungsrichtung ab\n\n"
            "📵 NICHT filmen — in Deckung gehen"
        ),
        "cruise": (
            "✈️ *MARSCHFLUGKÖRPER — IN DECKUNG*\n\n"
            "✅ *SOFORT:*\n"
            "• Tiefgarage oder Keller — Priorität Nr. 1\n"
            "• So weit wie möglich von Fenstern weg\n"
            "• Nicht im Freien stehen\n\n"
            "⚠️ Kalibr fliegt auf niedriger Höhe — Vorwarnung kann sehr kurz sein\n\n"
            "🔇 Gas abstellen, Fenster in einem anderen Raum öffnen (wegen Druckwelle)\n\n"
            "📞 Nach der Entwarnung: 101, 112"
        ),
        "fab": (
            "💣 *FAB-BOMBE — MAXIMALE BEDROHUNG*\n\n"
            "‼️ Zwei-Wände-Regel FUNKTIONIERT NICHT\n"
            "‼️ Tiefer Keller oder mehrstöckiger Bunker nötig\n\n"
            "✅ *SOFORT:*\n"
            "• Tiefer Bunker / Metro / Tiefgarage\n"
            "• NICHT in der Wohnung bleiben — auch nicht im Erdgeschoss\n"
            "• Wenn kein Schutzraum — mindestens 50m von Gebäuden entfernen\n"
            "• Lege dich in eine Grube/Senke, decke den Kopf ab\n\n"
            "📞 112 oder 101 — nach dem Einschlag"
        ),
        "chemical": (
            "☣️ *CHEMISCHE GEFAHR — RAUM ABDICHTEN*\n\n"
            "🔴 Anzeichen: ungewöhnlicher Geruch, Rauchwolke, Symptome bei Menschen\n\n"
            "✅ *SOFORT:*\n"
            "• ALLE Fenster und Türen DICHT schließen\n"
            "• Tuch anfeuchten — Mund und Nase bedecken\n"
            "• Höher gehen (die meisten Gase sind schwerer als Luft)\n"
            "• Ritzen mit Klebeband abkleben wenn vorhanden\n\n"
            "🚫 *NICHT ohne Schutz nach draußen*\n\n"
            "✅ *Wenn du draußen bist:*\n"
            "• Auf der Windseite bleiben\n"
            "• Kleidung ausziehen, Haut gründlich mit Wasser abspülen\n\n"
            "📞 101 — sofort"
        ),
        "rubble": (
            "🆘 *UNTER TRÜMMERN — WAS TUN*\n\n"
            "📱 *WENN DU UNTER TRÜMMERN BIST:*\n"
            "• Drücke den SOS-Knopf unten — sendet GPS\n"
            "• Klopfe ALLE 30 SEK an Rohre oder Beton\n"
            "• Mund mit Stoff gegen Staub bedecken\n"
            "• Ruhig atmen — Sauerstoff sparen\n"
            "• NICHT ständig schreien — du verlierst Kraft\n\n"
            "👥 *WENN DU JEMANDEN SUCHST:*\n"
            "• Rufe 101 an — ERSTE PRIORITÄT\n"
            "• Höre alle 2 Minuten hin: Klopfen, Stimme\n"
            "• KEINE großen Trümmer alleine bewegen\n"
            "• Letzten bekannten Ort über Bot prüfen (Knopf unten)"
        ),
        "allclear": (
            "✅ *ENTWARNUNG — GEFAHR IST VORBEI*\n\n"
            "Bevor du rausgehst:\n"
            "• 5–10 Minuten nach der offiziellen Entwarnung warten\n"
            "• Straße durchs Fenster prüfen bevor du gehst\n"
            "• Unbekannte Gegenstände auf der Straße nicht anfassen\n\n"
            "💬 Familie informieren dass du sicher bist (/status)\n\n"
            "📊 Familienstatus prüfen: /family_status"
        ),
    },
    "fr": {
        "uav": (
            "🚁 *MENACE UAV — AGIS MAINTENANT*\n\n"
            "✅ *IMMÉDIATEMENT:*\n"
            "• Éloigne-toi des fenêtres — allonge-toi sur le sol\n"
            "• Éteins les lumières, ferme les rideaux (bloque l'optique du drone)\n"
            "• NE sors PAS dehors — le drone suit les mouvements\n"
            "• Téléphone en silencieux, mais NE l'éteins PAS\n\n"
            "🏠 *ABRI (règle des deux murs):*\n"
            "Salle de bain ou couloir > sous-sol\n"
            "NE te cache PAS sous les escaliers (risque d'effondrement)\n\n"
            "💥 *APRÈS UNE EXPLOSION DANS UN RAYON DE 500m:*\n"
            "• Ferme les fenêtres (menace chimique)\n"
            "• Ne sors pas pendant 15 min (possible deuxième vague)\n"
            "• Appelle: 101 ou 112"
        ),
        "ballistic": (
            "🚀 *MENACE BALISTIQUE — LES SECONDES COMPTENT*\n\n"
            "⚡ Temps: 2–4 minutes avant l'impact\n\n"
            "✅ *SI TU AS LE TEMPS:*\n"
            "Sous-sol ou rez-de-chaussée, murs porteurs\n\n"
            "✅ *SI TU N'AS PAS LE TEMPS:*\n"
            "• Allonge-toi dans n'importe quelle dépression (fossé, passage souterrain)\n"
            "• Ouvre la bouche (onde de choc)\n"
            "• Couvre l'arrière de ta tête avec les mains\n"
            "• Tourne-toi dans la direction opposée à la menace\n\n"
            "📵 NE filme PAS — mets-toi à l'abri"
        ),
        "cruise": (
            "✈️ *MISSILE DE CROISIÈRE — METS-TOI À L'ABRI*\n\n"
            "✅ *IMMÉDIATEMENT:*\n"
            "• Parking souterrain ou sous-sol — priorité n°1\n"
            "• Reste le plus loin possible des fenêtres\n"
            "• Ne reste pas dans les espaces ouverts\n\n"
            "⚠️ Le Kalibr vole à basse altitude — l'alerte peut être très courte\n\n"
            "🔇 Coupe le gaz, ouvre une fenêtre dans une autre pièce (onde de choc)\n\n"
            "📞 Après fin d'alerte: 101, 112"
        ),
        "fab": (
            "💣 *BOMBE FAB — MENACE MAXIMALE*\n\n"
            "‼️ La règle des deux murs NE FONCTIONNE PAS\n"
            "‼️ Besoin d'un sous-sol PROFOND ou d'un abri anti-bombes multi-niveaux\n\n"
            "✅ *IMMÉDIATEMENT:*\n"
            "• Abri anti-bombes profond / métro / parking souterrain\n"
            "• NE reste PAS dans l'appartement — même au rez-de-chaussée\n"
            "• Si pas d'abri — éloigne-toi d'au moins 50m des bâtiments\n"
            "• Allonge-toi dans un trou/fossé, couvre ta tête\n\n"
            "📞 112 ou 101 — après l'impact"
        ),
        "chemical": (
            "☣️ *MENACE CHIMIQUE — SCELLE LA PIÈCE*\n\n"
            "🔴 Signes: odeur inhabituelle, nuage de fumée, symptômes chez des personnes\n\n"
            "✅ *IMMÉDIATEMENT:*\n"
            "• Ferme TOUTES les fenêtres et portes HERMÉTIQUEMENT\n"
            "• Mouille un tissu — couvre bouche et nez\n"
            "• Monte plus haut (la plupart des gaz sont plus lourds que l'air)\n"
            "• Colmate les fentes avec du ruban adhésif si disponible\n\n"
            "🚫 *NE sors PAS sans protection*\n\n"
            "✅ *Si tu es dehors:*\n"
            "• Reste du côté d'où vient le vent\n"
            "• Retire tes vêtements, rince abondamment la peau à l'eau\n\n"
            "📞 101 — immédiatement"
        ),
        "rubble": (
            "🆘 *SOUS LES DÉCOMBRES — QUE FAIRE*\n\n"
            "📱 *SI TU ES SOUS LES DÉCOMBRES:*\n"
            "• Appuie sur le bouton SOS ci-dessous — envoie le GPS\n"
            "• Frappe sur des tuyaux ou du béton TOUTES LES 30 SEC\n"
            "• Couvre ta bouche avec un tissu contre la poussière\n"
            "• Respire calmement — économise l'oxygène\n"
            "• NE crie PAS constamment — tu vas perdre des forces\n\n"
            "👥 *SI TU CHERCHES QUELQU'UN:*\n"
            "• Appelle le 101 — PRIORITÉ ABSOLUE\n"
            "• Écoute toutes les 2 minutes: coups, voix\n"
            "• NE déplace PAS seul de gros débris\n"
            "• Vérifie le dernier emplacement connu via le bot (bouton ci-dessous)"
        ),
        "allclear": (
            "✅ *FIN D'ALERTE — LE DANGER EST PASSÉ*\n\n"
            "Avant de sortir:\n"
            "• Attends 5–10 minutes après la fin d'alerte officielle\n"
            "• Observe la rue par la fenêtre avant de sortir\n"
            "• Ne touche pas les objets inconnus dans la rue\n\n"
            "💬 Informe tes proches que tu es en sécurité (/status)\n\n"
            "📊 Vérifie le statut de la famille: /family_status"
        ),
    },
    "pl": {
        "uav": (
            "🚁 *ZAGROŻENIE UAV — DZIAŁAJ TERAZ*\n\n"
            "✅ *NATYCHMIAST:*\n"
            "• Odsuń się od okien — połóż się na podłodze\n"
            "• Wyłącz światło, zamknij zasłony (blokuje optykę drona)\n"
            "• NIE wychodź na zewnątrz — dron śledzi ruch\n"
            "• Telefon na ciszo, ale NIE wyłączaj\n\n"
            "🏠 *SCHRONIENIE (zasada dwóch ścian):*\n"
            "Łazienka lub korytarz > piwnica\n"
            "NIE chowaj się pod schodami (ryzyko zawalenia)\n\n"
            "💥 *PO WYBUCHU W PROMIENIU 500m:*\n"
            "• Zamknij okna (zagrożenie chemiczne)\n"
            "• Nie wychodź przez 15 min (możliwa druga fala)\n"
            "• Zadzwoń: 101 lub 112"
        ),
        "ballistic": (
            "🚀 *ZAGROŻENIE BALISTYCZNE — SEKUNDY DECYDUJĄ*\n\n"
            "⚡ Czas: 2–4 minuty do uderzenia\n\n"
            "✅ *JEŚLI MASZ CZAS:*\n"
            "Piwnica lub parter, ściany nośne\n\n"
            "✅ *JEŚLI NIE ZDĄŻYSZ:*\n"
            "• Połóż się w dowolnym zagłębieniu (rów, przejście podziemne)\n"
            "• Otwórz usta (fala uderzeniowa)\n"
            "• Zakryj tył głowy rękami\n"
            "• Odwróć się od kierunku zagrożenia\n\n"
            "📵 NIE nagrywaj — idź do schronienia"
        ),
        "cruise": (
            "✈️ *POCISK MANEWRUJĄCY — KRYJ SIĘ*\n\n"
            "✅ *NATYCHMIAST:*\n"
            "• Parking podziemny lub piwnica — priorytet nr 1\n"
            "• Trzymaj się jak najdalej od okien\n"
            "• Nie stój w otwartych przestrzeniach\n\n"
            "⚠️ Kalibr leci na małej wysokości — ostrzeżenie może być bardzo krótkie\n\n"
            "🔇 Zakręć gaz, otwórz okno w innym pokoju (fala uderzeniowa)\n\n"
            "📞 Po odwołaniu: 101, 112"
        ),
        "fab": (
            "💣 *BOMBA FAB — MAKSYMALNE ZAGROŻENIE*\n\n"
            "‼️ Zasada dwóch ścian NIE DZIAŁA\n"
            "‼️ Potrzebna GŁĘBOKA piwnica lub wielopoziomowy schron\n\n"
            "✅ *NATYCHMIAST:*\n"
            "• Głęboki schron / metro / parking podziemny\n"
            "• NIE zostawaj w mieszkaniu — nawet na parterze\n"
            "• Jeśli nie ma schronienia — odejdź co najmniej 50m od budynków\n"
            "• Połóż się w dołku/rowie, zakryj głowę\n\n"
            "📞 112 lub 101 — po uderzeniu"
        ),
        "chemical": (
            "☣️ *ZAGROŻENIE CHEMICZNE — USZCZELNIJ POMIESZCZENIE*\n\n"
            "🔴 Oznaki: niezwykły zapach, chmura dymu, objawy u ludzi\n\n"
            "✅ *NATYCHMIAST:*\n"
            "• Zamknij WSZYSTKIE okna i drzwi SZCZELNIE\n"
            "• Zwilż tkaninę — zakryj usta i nos\n"
            "• Idź wyżej (większość gazów jest cięższa od powietrza)\n"
            "• Oklej szczeliny taśmą jeśli masz\n\n"
            "🚫 *NIE wychodź bez ochrony*\n\n"
            "✅ *Jeśli jesteś na zewnątrz:*\n"
            "• Trzymaj się po nawietrznej stronie\n"
            "• Zdejmij odzież, obficie spłukuj skórę wodą\n\n"
            "📞 101 — natychmiast"
        ),
        "rubble": (
            "🆘 *POD GRUZAMI — CO ROBIĆ*\n\n"
            "📱 *JEŚLI JESTEŚ POD GRUZAMI:*\n"
            "• Naciśnij przycisk SOS poniżej — wysyła GPS\n"
            "• Pukaj w rury lub beton CO 30 SEK\n"
            "• Zakryj usta tkaniną przed kurzem\n"
            "• Oddychaj spokojnie — oszczędzaj tlen\n"
            "• NIE krzycz ciągle — stracisz siły\n\n"
            "👥 *JEŚLI SZUKASZ OSOBY:*\n"
            "• Zadzwoń 101 — PIERWSZEŃSTWO\n"
            "• Słuchaj co 2 minuty: pukanie, głos\n"
            "• NIE przesuwaj dużych gruzu samodzielnie\n"
            "• Sprawdź ostatnie znane miejsce przez bota (przycisk poniżej)"
        ),
        "allclear": (
            "✅ *ODWOŁANIE ALARMU — NIEBEZPIECZEŃSTWO MINĘŁO*\n\n"
            "Przed wyjściem:\n"
            "• Zaczekaj 5–10 minut po oficjalnym odwołaniu\n"
            "• Sprawdź ulicę przez okno przed wyjściem\n"
            "• Nie dotykaj nieznanych przedmiotów na ulicy\n\n"
            "💬 Poinformuj rodzinę że jesteś bezpieczny (/status)\n\n"
            "📊 Sprawdź status rodziny: /family_status"
        ),
    },
}


def get_template_text(lang: str, key: str) -> str:
    """Return localized threat template text. Falls back to Ukrainian."""
    lang_templates = _TEMPLATES_I18N.get(lang, _TEMPLATES_I18N["uk"])
    return lang_templates.get(key, _TEMPLATES_I18N["uk"].get(key, ""))
