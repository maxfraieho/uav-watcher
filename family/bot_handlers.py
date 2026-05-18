"""
Family safety group bot command handlers.
Uses db/models.py for persistence and Telethon bot API for notifications.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def _fmt_last_seen(ts_str) -> str:
    if not ts_str:
        return "невідомо"
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = datetime.now(timezone.utc) - dt
        minutes = int(diff.total_seconds() // 60)
        if minutes < 1:
            return "щойно"
        if minutes < 60:
            return f"{minutes} хв тому"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} год тому"
        return f"{hours // 24} дн тому"
    except Exception:
        return str(ts_str)


async def _make_alert_call(user_client, target_user_id: int):
    """Place a Telegram voice call — rings even on silent mode."""
    from telethon.tl.functions.phone import RequestCallRequest
    from telethon.tl.types import PhoneCallProtocol
    try:
        await user_client(RequestCallRequest(
            user_id=target_user_id,
            random_id=int.from_bytes(os.urandom(4), "big"),
            g_a_hash=os.urandom(256),
            protocol=PhoneCallProtocol(
                udp_p2p=True,
                udp_reflector=True,
                min_layer=65,
                max_layer=92,
                library_versions=["3.0.0"],
            ),
        ))
        log.info(f"Alert call placed to user {target_user_id}")
    except Exception as e:
        log.error(f"Alert call failed to {target_user_id}: {e}")


def register_family_handlers(bot_client, cfg, user_client=None):
    """Register all family-related event handlers on the bot client."""
    from telethon import events
    from db.models import (
        init_db, create_family, join_family,
        get_family_members, get_user_families,
        start_rollcall, record_rollcall_response, get_rollcall_status,
        update_last_seen,
    )

    init_db()

    @bot_client.on(events.NewMessage(pattern=r'^/family_create(.*)'))
    async def cmd_family_create(event):
        sender = await event.get_sender()
        name = (event.pattern_match.group(1) or "").strip()
        if not name:
            await event.respond(
                "Вкажи назву сімейної групи:\n`/family_create Моя родина`",
                parse_mode='md'
            )
            return
        family = create_family(name, sender.id)
        await event.respond(
            f"Сімейну групу створено!\n\n"
            f"Назва: {family['name']}\n"
            f"Код запрошення: `{family['invite_code']}`\n\n"
            f"Поділись кодом з рідними:\n"
            f"`/family_join {family['invite_code']}`",
            parse_mode='md'
        )

    @bot_client.on(events.NewMessage(pattern=r'^/family_join(.*)'))
    async def cmd_family_join(event):
        sender = await event.get_sender()
        code = (event.pattern_match.group(1) or "").strip().upper()
        if not code:
            await event.respond(
                "Вкажи код запрошення:\n`/family_join КОД`",
                parse_mode='md'
            )
            return
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Учасник"
        family = join_family(code, sender.id, sender.username, name)
        if family:
            await event.respond(
                f"Ти доданий до сімї *{family['name']}*!\n"
                f"При наступній тривозі бот запитає: чи ти в безпеці.",
                parse_mode='md'
            )
        else:
            await event.respond("Код не знайдено. Перевір правильність.")

    @bot_client.on(events.NewMessage(pattern=r'^/family_status'))
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
        lines = []
        for f in families:
            members = get_family_members(f['id'])
            lines.append(f"*{f['name']}* (код: `{f['invite_code']}`)")
            for m in members:
                last = _fmt_last_seen(m.get("last_seen"))
                note = m.get("ok_note") or ""
                note_str = f" — {note}" if note else ""
                marker = "" if m["user_id"] == sender.id else ""
                lines.append(f"  {marker}{m['name']}: {last}{note_str}")
        await event.respond("\n".join(lines), parse_mode='md')

    @bot_client.on(events.NewMessage(pattern=r'^/ok(.*)'))
    async def cmd_ok(event):
        sender = await event.get_sender()
        note = (event.pattern_match.group(1) or "").strip()
        update_last_seen(sender.id, note or None)
        families = get_user_families(sender.id)
        sender_name = sender.first_name or str(sender.id)
        msg = f"{sender_name}: в порядку"
        if note:
            msg += f" — {note}"
        for family in families:
            members = get_family_members(family['id'])
            for m in members:
                if m['user_id'] != sender.id:
                    try:
                        await bot_client.send_message(m['user_id'], msg)
                    except Exception as e:
                        log.warning(f"Could not notify {m['user_id']}: {e}")
        reply = "Статус оновлено: в порядку"
        if note:
            reply += f" — {note}"
        await event.respond(reply)

    @bot_client.on(events.NewMessage(pattern=r'^/sos|^/SOS'))
    async def cmd_sos(event):
        sender = await event.get_sender()
        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "Учасник"
        families = get_user_families(sender.id)
        if not families:
            await event.respond("Ти не в жодній сімейній групі.\n/family_join КОД")
            return
        sos_msg = f"SOS від {name}! Потрібна допомога! Зателефонуй негайно."
        await event.respond("SOS надіслано всім членам твоїх сімейних груп.")
        for family in families:
            members = get_family_members(family['id'])
            for m in members:
                if m['user_id'] != sender.id:
                    try:
                        await bot_client.send_message(m['user_id'], sos_msg)
                    except Exception as e:
                        log.error(f"SOS delivery failed to {m['user_id']}: {e}")
                    if user_client:
                        await asyncio.sleep(1)
                        await _make_alert_call(user_client, m['user_id'])

    # Rollcall inline button responses
    @bot_client.on(events.CallbackQuery(pattern=b'rc_(safe|sos)_(.+)'))
    async def handle_rollcall_response(event):
        data = event.data.decode()
        parts = data.split('_')
        status = parts[1]
        rollcall_id = int(parts[2])
        sender = await event.get_sender()
        record_rollcall_response(rollcall_id, sender.id, status)
        update_last_seen(sender.id, "відповів на перевірку" if status == 'safe' else "SOS на перевірці")
        label = "Відповідь збережено: В БЕЗПЕЦІ" if status == 'safe' else "Відповідь збережено: ПОТРІБНА ДОПОМОГА"
        await event.edit(label)
        await event.answer()

    # Passive last_seen tracking — update on any private message
    @bot_client.on(events.NewMessage())
    async def passive_tracker(event):
        if event.is_private:
            try:
                update_last_seen(event.sender_id)
            except Exception:
                pass

    @bot_client.on(events.NewMessage(pattern=r'^/shelter'))
    async def cmd_shelter(event):
        sender = await event.get_sender()
        import sqlite3 as _sqlite3
        from db.models import DB_PATH
        conn = _sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT lat, lon FROM location_checkins WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
            (sender.id,)
        ).fetchone()
        conn.close()
        if not row or not row[0]:
            await event.respond(
                "Не знаю твоєї локації.\n"
                "Надішли геолокацію командою /location, потім знову /shelter"
            )
            return
        await event.respond("🔍 Шукаю укриття поблизу...")
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
        from shelter_search import find_shelters_enhanced, format_shelters_for_chat
        try:
            shelters = await find_shelters_enhanced(user_client, row[0], row[1])
            text = format_shelters_for_chat(shelters)
        except Exception as e:
            log.error(f"/shelter error: {e}")
            text = "Помилка пошуку. Використай @e_shelter_bot"
        await event.respond(text)

    log.info("Family bot handlers registered.")
    return {
        'rollcall': lambda family_id, threat_type: run_rollcall(
            bot_client, cfg, family_id, threat_type, user_client=user_client
        )
    }


async def run_rollcall(bot_client, cfg: dict, family_id: int, threat_type: str, user_client=None):
    """
    Trigger automatic rollcall for a family when threat is detected.
    Sends inline buttons: V Bezpetsi / SOS
    After 10 minutes — calls non-responders via Telegram voice call.
    """
    from db.models import get_family_members, start_rollcall, get_rollcall_status
    from rescue.location_tracker import get_last_location

    rollcall_id = start_rollcall(family_id, threat_type)
    members = get_family_members(family_id)

    threat_labels = {
        'air_raid': 'Повітряна тривога',
        'uav': 'Загроза БПЛА',
        'ballistic': 'Балістична загроза',
    }
    label = threat_labels.get(threat_type, f'Загроза: {threat_type}')

    msg = (
        f"{label}\n\n"
        f"Підтвердь свій статус:\n"
        f"Маєш 10 хвилин — інакше буде надіслано сигнал тривоги."
    )
    buttons = [[
        {"text": "В БЕЗПЕЦІ", "callback_data": f"rc_safe_{rollcall_id}"},
        {"text": "ПОТРІБНА ДОПОМОГА", "callback_data": f"rc_sos_{rollcall_id}"}
    ]]

    for i, member in enumerate(members):
        try:
            await bot_client.send_message(
                member['user_id'],
                msg,
                buttons=buttons,
            )
        except Exception as e:
            log.error(f"Rollcall delivery failed to {member['user_id']}: {e}")
        if i < len(members) - 1:
            await asyncio.sleep(0.05)

    await asyncio.sleep(600)

    status = get_rollcall_status(rollcall_id)
    for detail in status['details']:
        if detail['status'] == 'no_response':
            try:
                loc = get_last_location(detail['user_id'])
            except Exception:
                loc = None
            if loc:
                loc_link = f"https://maps.google.com/?q={loc['lat']},{loc['lon']}"
                loc_info = f"\nОстаннє відоме місце: {loc_link}\n{loc['updated_at']}"
            else:
                loc_info = "\nГеолокація не збережена."
            alert_msg = (
                f"{detail['name']} не відповів протягом 10 хвилин!\n"
                f"Можливо потрібна допомога. Зателефонуй або перевір.{loc_info}"
            )
            for other in members:
                if other['user_id'] != detail['user_id']:
                    try:
                        await bot_client.send_message(other['user_id'], alert_msg)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        log.error(f"No-response alert failed: {e}")

            # Ring the non-responder directly
            if user_client:
                await asyncio.sleep(2)
                await _make_alert_call(user_client, detail['user_id'])
