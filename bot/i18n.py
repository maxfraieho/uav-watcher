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
        "threats_query": "Яка зараз обстановка? Що написали канали за останню годину?",
        "threats_err": "Не вдалось отримати дані.\nЕкстрені: 101 (ДСНС), 112",
        "chat_err": "Вибач, зараз не можу відповісти.\nЕкстрені: 101 (ДСНС), 112",
        "lang_chosen": "🇺🇦 Мову змінено на Українську.",
        "lang_prompt": "🌐 *Оберіть мову / Choose language:*",
        "detail_btn": "📡 Деталізуй з каналів",
        "detail_wait": "⏳ Збираю дані з каналів...",
        "detail_err": "Не вдалось отримати дані з каналів.",
        "threat_menu_title": "🛡 *Оберіть тип загрози:*",
        "help_title": "🛡 *Sharon — Кризовий консультант*\n\nОберіть тип загрози:",
        "llm_lang_instruction": "",
        # city switch
        "setcity_header": "📍 *Поточне місто моніторингу:* {city}",
        "setcity_choose": "Оберіть нове місто або натисніть «Ввести вручну»:",
        "setcity_manual_btn": "✏️ Ввести вручну...",
        "setcity_manual_prompt": (
            "✏️ Надішли назву міста або GPS-координати:\n\n"
            "Приклади:\n"
            "`/setcity Кропивницький`\n"
            "`/setcity 48.5079, 32.2623`"
        ),
        "setcity_geocoding": "🔍 Геокодую: *{city}*...",
        "setcity_not_found": (
            "❌ Не знайшов *{city}* в Nominatim.\n\n"
            "Спробуй точнішу назву або GPS:\n`/setcity 48.5079, 32.2623`"
        ),
        "setcity_parse_err": "❌ Не зрозумів. Спробуй: `/setcity Кропивницький`",
        "setcity_preset_err": "❌ Пресет не знайдено.",
        "setcity_success": (
            "✅ *Моніторинг перемкнуто на:*\n\n"
            "🏙 Місто: *{city}*{region_line}\n"
            "🗺 Координати: `{lat:.4f}, {lon:.4f}`\n"
            "🔑 Ключові слова: `{kws}`\n\n"
            "_Зміна набула чинності без перезапуску._"
        ),
        "setcity_error": "❌ Помилка при зміні міста: {error}",
        "setcity_region_label": "📍 Область",
        # family
        "family_create_usage": "Вкажи назву сімейної групи:\n`/family_create Моя родина`",
        "family_created": (
            "Сімейну групу створено!\n\n"
            "Назва: {name}\nКод запрошення: `{code}`\n\n"
            "Поділись кодом з рідними:\n`/family_join {code}`"
        ),
        "family_join_usage": "Вкажи код запрошення:\n`/family_join КОД`",
        "family_joined": "Ти доданий до сім'ї *{name}*!\nПри наступній тривозі бот запитає: чи ти в безпеці.",
        "family_join_err": "Код не знайдено. Перевір правильність.",
        "family_no_groups": (
            "У тебе немає сімейних груп.\n"
            "Створи: `/family_create Назва`\n"
            "або приєднайся: `/family_join КОД`"
        ),
        "family_ok_note": "в порядку",
        "family_ok_updated": "Статус оновлено: в порядку",
        "family_sos_sent": "SOS надіслано всім членам твоїх сімейних груп.",
        "family_sos_no_group": "Ти не в жодній сімейній групі.\n/family_join КОД",
        "shelter_no_location": "Не знаю твоєї локації.\nНадішли геолокацію командою /location, потім знову /shelter",
        "shelter_searching": "🔍 Шукаю укриття поблизу...",
        "shelter_error": "Помилка пошуку. Використай @e_shelter_bot",
        "rollcall_safe_btn": "В БЕЗПЕЦІ",
        "rollcall_sos_btn": "ПОТРІБНА ДОПОМОГА",
        "rollcall_safe_response": "Відповідь збережена: В БЕЗПЕЦІ",
        "rollcall_sos_response": "Відповідь збережена: ПОТРІБНА ДОПОМОГА",
        "rollcall_answered": "відповів на перевірку",
        # relative time
        "fmt_just_now": "щойно",
        "fmt_minutes_ago": "{n} хв тому",
        "fmt_hours_ago": "{n} год тому",
        "fmt_days_ago": "{n} дн тому",
        "fmt_unknown": "невідомо",
        # checkin / location
        "checkin_prompt": (
            "📍 *Надішли свою геолокацію*\n\n"
            "Натисни скрепку 📎 → Геолокація → Надіслати поточне місцезнаходження.\n\n"
            "Вона буде збережена як твоє останнє відоме місцезнаходження "
            "і передана рідним якщо ти не відповіси на rollcall."
        ),
        "location_saved": "📍 Геолокацію збережено. Шукаю укриття поблизу...",
        "shelter_auto_err": "Помилка пошуку укриттів. Використай @e_shelter_bot",
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
        "threats_query": "What's the current situation? What did the channels report in the last hour?",
        "threats_err": "Couldn't retrieve data.\nEmergency: 101 (DSNS), 112",
        "chat_err": "Sorry, I can't respond right now.\nEmergency: 101 (DSNS), 112",
        "lang_chosen": "🇬🇧 Language changed to English.",
        "lang_prompt": "🌐 *Choose language / Оберіть мову:*",
        "detail_btn": "📡 Detail from channels",
        "detail_wait": "⏳ Collecting data from channels...",
        "detail_err": "Couldn't retrieve data from channels.",
        "threat_menu_title": "🛡 *Choose threat type:*",
        "help_title": "🛡 *Sharon — Crisis Assistant*\n\nChoose threat type:",
        "llm_lang_instruction": "\n\nIMPORTANT: Always respond in English regardless of the language the user writes in.",
        # city switch
        "setcity_header": "📍 *Current monitoring city:* {city}",
        "setcity_choose": "Choose a city or tap «Enter manually»:",
        "setcity_manual_btn": "✏️ Enter manually...",
        "setcity_manual_prompt": (
            "✏️ Send city name or GPS coordinates:\n\n"
            "Examples:\n"
            "`/setcity Kropyvnytskyi`\n"
            "`/setcity 48.5079, 32.2623`"
        ),
        "setcity_geocoding": "🔍 Geocoding: *{city}*...",
        "setcity_not_found": (
            "❌ Couldn't find *{city}* in Nominatim.\n\n"
            "Try a more precise name or GPS:\n`/setcity 48.5079, 32.2623`"
        ),
        "setcity_parse_err": "❌ Didn't understand. Try: `/setcity Kropyvnytskyi`",
        "setcity_preset_err": "❌ Preset not found.",
        "setcity_success": (
            "✅ *Monitoring switched to:*\n\n"
            "🏙 City: *{city}*{region_line}\n"
            "🗺 Coordinates: `{lat:.4f}, {lon:.4f}`\n"
            "🔑 Keywords: `{kws}`\n\n"
            "_Change applied without restart._"
        ),
        "setcity_error": "❌ Error changing city: {error}",
        "setcity_region_label": "📍 Region",
        # family
        "family_create_usage": "Enter a name for the family group:\n`/family_create My Family`",
        "family_created": (
            "Family group created!\n\n"
            "Name: {name}\nInvite code: `{code}`\n\n"
            "Share the code with family:\n`/family_join {code}`"
        ),
        "family_join_usage": "Enter the invite code:\n`/family_join CODE`",
        "family_joined": "You have joined *{name}*!\nDuring the next alert the bot will check: are you safe.",
        "family_join_err": "Code not found. Check it's correct.",
        "family_no_groups": (
            "You have no family groups.\n"
            "Create: `/family_create Name`\n"
            "or join: `/family_join CODE`"
        ),
        "family_ok_note": "ok",
        "family_ok_updated": "Status updated: ok",
        "family_sos_sent": "SOS sent to all members of your family groups.",
        "family_sos_no_group": "You are not in any family group.\n/family_join CODE",
        "shelter_no_location": "I don't know your location.\nSend your location with /location, then /shelter again",
        "shelter_searching": "🔍 Searching for shelters nearby...",
        "shelter_error": "Search failed. Use @e_shelter_bot",
        "rollcall_safe_btn": "I'M SAFE",
        "rollcall_sos_btn": "I NEED HELP",
        "rollcall_safe_response": "Response saved: SAFE",
        "rollcall_sos_response": "Response saved: NEED HELP",
        "rollcall_answered": "answered rollcall",
        # relative time
        "fmt_just_now": "just now",
        "fmt_minutes_ago": "{n} min ago",
        "fmt_hours_ago": "{n} hr ago",
        "fmt_days_ago": "{n} days ago",
        "fmt_unknown": "unknown",
        # checkin / location
        "checkin_prompt": (
            "📍 *Send your location*\n\n"
            "Tap the paperclip 📎 → Location → Send current location.\n\n"
            "It will be saved as your last known location "
            "and shared with family if you don't respond to a rollcall."
        ),
        "location_saved": "📍 Location saved. Searching for nearby shelters...",
        "shelter_auto_err": "Error finding shelters. Use @e_shelter_bot",
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
        "threats_query": "Wie ist die aktuelle Lage? Was haben die Kanäle in der letzten Stunde gemeldet?",
        "threats_err": "Daten konnten nicht abgerufen werden.\nNotfall: 101 (DSNS), 112",
        "chat_err": "Entschuldigung, ich kann gerade nicht antworten.\nNotfall: 101 (DSNS), 112",
        "lang_chosen": "🇩🇪 Sprache auf Deutsch geändert.",
        "lang_prompt": "🌐 *Sprache wählen / Оберіть мову:*",
        "detail_btn": "📡 Details aus Kanälen",
        "detail_wait": "⏳ Sammle Daten aus Kanälen...",
        "detail_err": "Daten aus Kanälen konnten nicht abgerufen werden.",
        "threat_menu_title": "🛡 *Bedrohungstyp wählen:*",
        "help_title": "🛡 *Sharon — Krisenassistent*\n\nBedrohungstyp wählen:",
        "llm_lang_instruction": "\n\nWICHTIG: Antworte immer auf Deutsch, egal in welcher Sprache der Nutzer schreibt.",
        # city switch
        "setcity_header": "📍 *Aktuelle Überwachungsstadt:* {city}",
        "setcity_choose": "Wähle eine Stadt oder tippe «Manuell eingeben»:",
        "setcity_manual_btn": "✏️ Manuell eingeben...",
        "setcity_manual_prompt": (
            "✏️ Sende Stadtname oder GPS-Koordinaten:\n\n"
            "Beispiele:\n"
            "`/setcity Kropyvnytskyi`\n"
            "`/setcity 48.5079, 32.2623`"
        ),
        "setcity_geocoding": "🔍 Geocodierung: *{city}*...",
        "setcity_not_found": (
            "❌ *{city}* nicht in Nominatim gefunden.\n\n"
            "Versuch einen genaueren Namen oder GPS:\n`/setcity 48.5079, 32.2623`"
        ),
        "setcity_parse_err": "❌ Nicht verstanden. Versuch: `/setcity Kropyvnytskyi`",
        "setcity_preset_err": "❌ Preset nicht gefunden.",
        "setcity_success": (
            "✅ *Überwachung umgeschaltet auf:*\n\n"
            "🏙 Stadt: *{city}*{region_line}\n"
            "🗺 Koordinaten: `{lat:.4f}, {lon:.4f}`\n"
            "🔑 Schlüsselwörter: `{kws}`\n\n"
            "_Änderung ohne Neustart aktiv._"
        ),
        "setcity_error": "❌ Fehler beim Stadtwechsel: {error}",
        "setcity_region_label": "📍 Region",
        # family
        "family_create_usage": "Gib einen Namen für die Familiengruppe an:\n`/family_create Meine Familie`",
        "family_created": (
            "Familiengruppe erstellt!\n\n"
            "Name: {name}\nEinladungscode: `{code}`\n\n"
            "Teile den Code mit deiner Familie:\n`/family_join {code}`"
        ),
        "family_join_usage": "Gib den Einladungscode ein:\n`/family_join CODE`",
        "family_joined": "Du bist *{name}* beigetreten!\nBeim nächsten Alarm fragt der Bot: Bist du in Sicherheit.",
        "family_join_err": "Code nicht gefunden. Überprüfe die Richtigkeit.",
        "family_no_groups": (
            "Du hast keine Familiengruppen.\n"
            "Erstellen: `/family_create Name`\n"
            "oder beitreten: `/family_join CODE`"
        ),
        "family_ok_note": "in Ordnung",
        "family_ok_updated": "Status aktualisiert: in Ordnung",
        "family_sos_sent": "SOS an alle Mitglieder deiner Familiengruppen gesendet.",
        "family_sos_no_group": "Du bist in keiner Familiengruppe.\n/family_join CODE",
        "shelter_no_location": "Ich kenne deinen Standort nicht.\nSende deinen Standort mit /location, dann erneut /shelter",
        "shelter_searching": "🔍 Suche Schutzräume in der Nähe...",
        "shelter_error": "Suche fehlgeschlagen. Nutze @e_shelter_bot",
        "rollcall_safe_btn": "IN SICHERHEIT",
        "rollcall_sos_btn": "BRAUCHE HILFE",
        "rollcall_safe_response": "Antwort gespeichert: IN SICHERHEIT",
        "rollcall_sos_response": "Antwort gespeichert: BRAUCHE HILFE",
        "rollcall_answered": "auf Überprüfung geantwortet",
        # relative time
        "fmt_just_now": "gerade eben",
        "fmt_minutes_ago": "vor {n} Min",
        "fmt_hours_ago": "vor {n} Std",
        "fmt_days_ago": "vor {n} Tagen",
        "fmt_unknown": "unbekannt",
        # checkin / location
        "checkin_prompt": (
            "📍 *Sende deinen Standort*\n\n"
            "Tippe auf 📎 → Standort → Aktuellen Standort senden.\n\n"
            "Er wird als dein letzter bekannter Standort gespeichert "
            "und an deine Familie weitergegeben, wenn du nicht auf einen Rollcall antwortest."
        ),
        "location_saved": "📍 Standort gespeichert. Suche Schutzräume in der Nähe...",
        "shelter_auto_err": "Fehler bei der Suche. Nutze @e_shelter_bot",
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
        "threats_query": "Quelle est la situation actuelle ? Qu'ont rapporté les canaux dans la dernière heure ?",
        "threats_err": "Impossible de récupérer les données.\nUrgence: 101 (DSNS), 112",
        "chat_err": "Désolé, je ne peux pas répondre maintenant.\nUrgence: 101 (DSNS), 112",
        "lang_chosen": "🇫🇷 Langue changée en Français.",
        "lang_prompt": "🌐 *Choisir la langue / Оберіть мову:*",
        "detail_btn": "📡 Détails des canaux",
        "detail_wait": "⏳ Collecte de données...",
        "detail_err": "Impossible de récupérer les données des canaux.",
        "threat_menu_title": "🛡 *Choisir le type de menace:*",
        "help_title": "🛡 *Sharon — Assistant de crise*\n\nChoisir le type de menace:",
        "llm_lang_instruction": "\n\nIMPORTANT: Répondez toujours en français quelle que soit la langue de l'utilisateur.",
        # city switch
        "setcity_header": "📍 *Ville de surveillance actuelle:* {city}",
        "setcity_choose": "Choisissez une ville ou appuyez sur «Saisir manuellement»:",
        "setcity_manual_btn": "✏️ Saisir manuellement...",
        "setcity_manual_prompt": (
            "✏️ Envoyez le nom de la ville ou des coordonnées GPS:\n\n"
            "Exemples:\n"
            "`/setcity Kropyvnytskyi`\n"
            "`/setcity 48.5079, 32.2623`"
        ),
        "setcity_geocoding": "🔍 Géocodage: *{city}*...",
        "setcity_not_found": (
            "❌ *{city}* introuvable dans Nominatim.\n\n"
            "Essayez un nom plus précis ou GPS:\n`/setcity 48.5079, 32.2623`"
        ),
        "setcity_parse_err": "❌ Non compris. Essayez: `/setcity Kropyvnytskyi`",
        "setcity_preset_err": "❌ Preset introuvable.",
        "setcity_success": (
            "✅ *Surveillance basculée sur:*\n\n"
            "🏙 Ville: *{city}*{region_line}\n"
            "🗺 Coordonnées: `{lat:.4f}, {lon:.4f}`\n"
            "🔑 Mots-clés: `{kws}`\n\n"
            "_Changement appliqué sans redémarrage._"
        ),
        "setcity_error": "❌ Erreur lors du changement de ville: {error}",
        "setcity_region_label": "📍 Région",
        # family
        "family_create_usage": "Donne un nom au groupe familial:\n`/family_create Ma Famille`",
        "family_created": (
            "Groupe familial créé!\n\n"
            "Nom: {name}\nCode d'invitation: `{code}`\n\n"
            "Partage le code avec ta famille:\n`/family_join {code}`"
        ),
        "family_join_usage": "Entre le code d'invitation:\n`/family_join CODE`",
        "family_joined": "Tu as rejoint *{name}*!\nLors de la prochaine alerte le bot te demandera: es-tu en sécurité.",
        "family_join_err": "Code introuvable. Vérifiez qu'il est correct.",
        "family_no_groups": (
            "Tu n'as aucun groupe familial.\n"
            "Créer: `/family_create Nom`\n"
            "ou rejoindre: `/family_join CODE`"
        ),
        "family_ok_note": "ok",
        "family_ok_updated": "Statut mis à jour: ok",
        "family_sos_sent": "SOS envoyé à tous les membres de tes groupes familiaux.",
        "family_sos_no_group": "Tu n'es dans aucun groupe familial.\n/family_join CODE",
        "shelter_no_location": "Je ne connais pas ta position.\nEnvoie ta localisation avec /location, puis à nouveau /shelter",
        "shelter_searching": "🔍 Recherche d'abris à proximité...",
        "shelter_error": "Recherche échouée. Utilise @e_shelter_bot",
        "rollcall_safe_btn": "EN SÉCURITÉ",
        "rollcall_sos_btn": "J'AI BESOIN D'AIDE",
        "rollcall_safe_response": "Réponse enregistrée: EN SÉCURITÉ",
        "rollcall_sos_response": "Réponse enregistrée: BESOIN D'AIDE",
        "rollcall_answered": "a répondu à l'appel",
        # relative time
        "fmt_just_now": "à l'instant",
        "fmt_minutes_ago": "il y a {n} min",
        "fmt_hours_ago": "il y a {n} h",
        "fmt_days_ago": "il y a {n} j",
        "fmt_unknown": "inconnu",
        # checkin / location
        "checkin_prompt": (
            "📍 *Envoie ta localisation*\n\n"
            "Appuie sur 📎 → Localisation → Envoyer la position actuelle.\n\n"
            "Elle sera enregistrée comme ta dernière position connue "
            "et transmise à ta famille si tu ne réponds pas à un appel."
        ),
        "location_saved": "📍 Localisation enregistrée. Recherche d'abris à proximité...",
        "shelter_auto_err": "Erreur lors de la recherche. Utilise @e_shelter_bot",
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
        "threats_query": "Jaka jest aktualna sytuacja? Co napisały kanały w ostatniej godzinie?",
        "grounding_intro": "🧘 *Technika uziemienia — zatrzymaj się i czytaj powoli:*\n\nTo pomoże ci wrócić do chwili obecnej.",
        "threats_err": "Nie udało się pobrać danych.\nNagłe: 101 (DSNS), 112",
        "chat_err": "Przepraszam, nie mogę teraz odpowiedzieć.\nNagłe: 101 (DSNS), 112",
        "lang_chosen": "🇵🇱 Język zmieniony na Polski.",
        "lang_prompt": "🌐 *Wybierz język / Оберіть мову:*",
        "detail_btn": "📡 Szczegóły z kanałów",
        "detail_wait": "⏳ Zbieram dane z kanałów...",
        "detail_err": "Nie udało się pobrać danych z kanałów.",
        "threat_menu_title": "🛡 *Wybierz typ zagrożenia:*",
        "help_title": "🛡 *Sharon — Asystent kryzysowy*\n\nWybierz typ zagrożenia:",
        "llm_lang_instruction": "\n\nWAŻNE: Zawsze odpowiadaj po polsku niezależnie od języka użytkownika.",
        # city switch
        "setcity_header": "📍 *Aktualne miasto monitorowania:* {city}",
        "setcity_choose": "Wybierz miasto lub naciśnij «Wprowadź ręcznie»:",
        "setcity_manual_btn": "✏️ Wprowadź ręcznie...",
        "setcity_manual_prompt": (
            "✏️ Wyślij nazwę miasta lub współrzędne GPS:\n\n"
            "Przykłady:\n"
            "`/setcity Kropyvnytskyi`\n"
            "`/setcity 48.5079, 32.2623`"
        ),
        "setcity_geocoding": "🔍 Geokodowanie: *{city}*...",
        "setcity_not_found": (
            "❌ Nie znalazłem *{city}* w Nominatim.\n\n"
            "Spróbuj dokładniejszej nazwy lub GPS:\n`/setcity 48.5079, 32.2623`"
        ),
        "setcity_parse_err": "❌ Nie zrozumiałem. Spróbuj: `/setcity Kropyvnytskyi`",
        "setcity_preset_err": "❌ Preset nie znaleziony.",
        "setcity_success": (
            "✅ *Monitorowanie przełączone na:*\n\n"
            "🏙 Miasto: *{city}*{region_line}\n"
            "🗺 Współrzędne: `{lat:.4f}, {lon:.4f}`\n"
            "🔑 Słowa kluczowe: `{kws}`\n\n"
            "_Zmiana aktywna bez restartu._"
        ),
        "setcity_error": "❌ Błąd podczas zmiany miasta: {error}",
        "setcity_region_label": "📍 Region",
        # family
        "family_create_usage": "Podaj nazwę grupy rodzinnej:\n`/family_create Moja Rodzina`",
        "family_created": (
            "Grupa rodzinna utworzona!\n\n"
            "Nazwa: {name}\nKod zaproszenia: `{code}`\n\n"
            "Udostępnij kod rodzinie:\n`/family_join {code}`"
        ),
        "family_join_usage": "Podaj kod zaproszenia:\n`/family_join KOD`",
        "family_joined": "Dołączyłeś do *{name}*!\nPodczas następnego alertu bot zapyta: czy jesteś bezpieczny.",
        "family_join_err": "Kod nie znaleziony. Sprawdź poprawność.",
        "family_no_groups": (
            "Nie masz grup rodzinnych.\n"
            "Utwórz: `/family_create Nazwa`\n"
            "lub dołącz: `/family_join KOD`"
        ),
        "family_ok_note": "ok",
        "family_ok_updated": "Status zaktualizowany: ok",
        "family_sos_sent": "SOS wysłany do wszystkich członków twoich grup rodzinnych.",
        "family_sos_no_group": "Nie należysz do żadnej grupy rodzinnej.\n/family_join KOD",
        "shelter_no_location": "Nie znam twojej lokalizacji.\nWyślij lokalizację przez /location, a następnie ponownie /shelter",
        "shelter_searching": "🔍 Szukam schronień w pobliżu...",
        "shelter_error": "Wyszukiwanie nieudane. Użyj @e_shelter_bot",
        "rollcall_safe_btn": "JESTEM BEZPIECZNY",
        "rollcall_sos_btn": "POTRZEBUJĘ POMOCY",
        "rollcall_safe_response": "Odpowiedź zapisana: BEZPIECZNY",
        "rollcall_sos_response": "Odpowiedź zapisana: POTRZEBUJĘ POMOCY",
        "rollcall_answered": "odpowiedział na apel",
        # relative time
        "fmt_just_now": "przed chwilą",
        "fmt_minutes_ago": "{n} min temu",
        "fmt_hours_ago": "{n} godz temu",
        "fmt_days_ago": "{n} dni temu",
        "fmt_unknown": "nieznane",
        # checkin / location
        "checkin_prompt": (
            "📍 *Wyślij swoją lokalizację*\n\n"
            "Naciśnij 📎 → Lokalizacja → Wyślij bieżącą lokalizację.\n\n"
            "Zostanie zapisana jako twoja ostatnia znana lokalizacja "
            "i przekazana rodzinie jeśli nie odpiszesz na apel."
        ),
        "location_saved": "📍 Lokalizacja zapisana. Szukam schronień w pobliżu...",
        "shelter_auto_err": "Błąd wyszukiwania. Użyj @e_shelter_bot",
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


def fmt_last_seen(lang: str, ts_str) -> str:
    """Format a last-seen timestamp into a localized relative string."""
    from datetime import datetime, timezone
    if not ts_str:
        return get(lang, "fmt_unknown")
    try:
        dt = datetime.fromisoformat(str(ts_str))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - dt
        minutes = int(diff.total_seconds() // 60)
        if minutes < 1:
            return get(lang, "fmt_just_now")
        if minutes < 60:
            return get(lang, "fmt_minutes_ago").format(n=minutes)
        hours = minutes // 60
        if hours < 24:
            return get(lang, "fmt_hours_ago").format(n=hours)
        return get(lang, "fmt_days_ago").format(n=hours // 24)
    except Exception:
        return str(ts_str)


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
