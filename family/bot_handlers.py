"""
Family safety group bot command handlers.
Uses db/models.py for persistence and Bot API for notifications.
"""
import asyncio
import logging
import httpx
from db.models import (init_db, create_family, join_family,
                       get_family_members, get_user_families,
                       start_rollcall, record_rollcall_response,
                       get_rollcall_status)

log = logging.getLogger(__name__)


def register_family_handlers(bot_client, cfg):
    """Register all family-related event handlers on the bot client."""
    from telethon import events

    init_db()

    @bot_client.on(events.NewMessage(pattern=r'/family_create (.+)'))
    async def cmd_family_create(event):
        sender = await event.get_sender()
        name = event.pattern_match.group(1).strip()
        family = create_family(name, sender.id)
        await event.respond(
            f"✅ *Сімейну групу створено!*\n\n"
            f"👨‍👩‍👧 Назва: {family['name']}\n"
            f"🔑 Код запрошення: `{family['invite_code']}`\n\n"
            f"Поділись кодом з рідними — вони приєднаються командою:\n"
            f"`/family_join {family['invite_code']}`",
            parse_mode='md'
        )

    @bot_client.on(events.NewMessage(pattern=r'/family_join (.+)'))
    async def cmd_family_join(event):
        sender = await event.get_sender()
        code = event.pattern_match.group(1).strip().upper()
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Учасник"
        family = join_family(code, sender.id, sender.username, name)
        if family:
            await event.respond(
                f"✅ Ти доданий до сім'ї *{family['name']}*!\n"
                f"При наступній тривозі бот запитає: чи ти в безпеці.",
                parse_mode='md'
            )
        else:
            await event.respond("❌ Код не знайдено. Перевір правильність.")

    @bot_client.on(events.NewMessage(pattern="/family_status|/сімя"))
    async def cmd_family_status(event):
        sender = await event.get_sender()
        families = get_user_families(sender.id)
        if not families:
            await event.respond(
                "У тебе немає сімейних груп.\n"
                "Створи: `/family_create Назва`\n"
                "або приєднайся: `/family_join КОД`",
                parse_mode='md'
            )
            return
        text = "👨‍👩‍👧 *Твої сімейні групи:*\n\n"
        for f in families:
            members = get_family_members(f['id'])
            text += f"• *{f['name']}* (код: `{f['invite_code']}`)\n"
            text += f"  Учасники: {len(members)}\n"
        await event.respond(text, parse_mode='md')

    @bot_client.on(events.NewMessage(pattern='/sos|/SOS'))
    async def cmd_sos(event):
        sender = await event.get_sender()
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Учасник"
        families = get_user_families(sender.id)
        if not families:
            await event.respond("❌ Ти не в жодній сімейній групі.\n/family_join КОД")
            return
        sos_msg = f"🆘🆘🆘 *ЕКСТРЕНИЙ СИГНАЛ SOS*\n\n{name} потребує допомоги!\n\nЗателефонуй негайно."
        await event.respond("🆘 SOS надіслано всім членам твоїх сімейних груп.")
        for family in families:
            members = get_family_members(family['id'])
            for m in members:
                if m['user_id'] != sender.id:
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            await client.post(
                                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                                json={'chat_id': m['user_id'], 'text': sos_msg, 'parse_mode': 'Markdown'}
                            )
                    except Exception as e:
                        log.error(f"SOS delivery failed to {m['user_id']}: {e}")

    # Rollcall inline button responses
    @bot_client.on(events.CallbackQuery(pattern=b'rc_(safe|sos)_(.+)'))
    async def handle_rollcall_response(event):
        data = event.data.decode()
        parts = data.split('_')
        status = parts[1]   # 'safe' or 'sos'
        rollcall_id = int(parts[2])
        sender = await event.get_sender()
        record_rollcall_response(rollcall_id, sender.id, status)
        label = "✅ Відповідь збережено: Ти В БЕЗПЕЦІ" if status == 'safe' else "🆘 Відповідь збережено: ПОТРІБНА ДОПОМОГА — очікуй зв'язку"
        await event.edit(label)
        await event.answer()

    log.info("Family bot handlers registered.")
    return {
        'rollcall': lambda family_id, threat_type: run_rollcall(bot_client, cfg, family_id, threat_type)
    }


async def run_rollcall(bot_client, cfg: dict, family_id: int, threat_type: str):
    """
    Trigger automatic rollcall for a family when threat is detected.
    Sends inline buttons: ✅ В безпеці / 🆘 Потрібна допомога
    After 10 minutes — alerts about non-responders.
    """
    rollcall_id = start_rollcall(family_id, threat_type)
    members = get_family_members(family_id)

    threat_labels = {
        'air_raid': '🚨 Повітряна тривога',
        'uav': '🚁 Загроза БПЛА',
        'ballistic': '🚀 Балістична загроза',
    }
    label = threat_labels.get(threat_type, f'⚠️ Загроза: {threat_type}')

    msg = (
        f"{label}\n\n"
        f"❓ Підтвердь свій статус:\n"
        f"Ти маєш 10 хвилин — інакше буде надіслано сигнал тривоги."
    )
    buttons = [[
        {"text": "✅ Я В БЕЗПЕЦІ", "callback_data": f"rc_safe_{rollcall_id}"},
        {"text": "🆘 ПОТРІБНА ДОПОМОГА", "callback_data": f"rc_sos_{rollcall_id}"}
    ]]

    for member in members:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                    json={
                        'chat_id': member['user_id'],
                        'text': msg,
                        'parse_mode': 'Markdown',
                        'reply_markup': {'inline_keyboard': buttons}
                    }
                )
        except Exception as e:
            log.error(f"Rollcall delivery failed to {member['user_id']}: {e}")

    await asyncio.sleep(600)

    status = get_rollcall_status(rollcall_id)
    from rescue.location_tracker import get_last_location
    for detail in status['details']:
        if detail['status'] == 'no_response':
            loc = get_last_location(detail['user_id'])
            if loc:
                loc_link = f"https://maps.google.com/?q={loc['lat']},{loc['lon']}"
                loc_info = f"\n📍 Останнє відоме місце: {loc_link}\n🕐 {loc['updated_at']}"
            else:
                loc_info = "\n📍 Геолокація не збережена."
            alert_msg = (
                f"⚠️ *{detail['name']}* не відповів протягом 10 хвилин!\n"
                f"Можливо потрібна допомога. Зателефонуй або перевір.{loc_info}"
            )
            for other in members:
                if other['user_id'] != detail['user_id']:
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            await client.post(
                                f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage",
                                json={'chat_id': other['user_id'], 'text': alert_msg, 'parse_mode': 'Markdown'}
                            )
                    except Exception as e:
                        log.error(f"No-response alert failed: {e}")
