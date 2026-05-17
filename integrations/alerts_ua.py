"""
Official Ukrainian air raid alert API integration.
Docs: https://devs.alerts.in.ua/
Runs in parallel with Telegram OSINT channel monitoring.
"""
import asyncio
import logging
from alerts_in_ua import AsyncClient as AlertsClient

log = logging.getLogger(__name__)


class AlertsUAPoller:
    def __init__(self, token: str, region: str, callback):
        """
        token: API key from alerts.in.ua (free for civilian use)
        region: Oblast name e.g. "Кіровоградська область"
        callback: async function(alert_type, location, started_at) called on new threat
        """
        self.client = AlertsClient(token=token)
        self.region = region
        self.callback = callback
        self.active_alerts = set()
        log.info(f"AlertsUA poller initialized for region: {region}")

    async def poll_loop(self, interval_seconds: int = 15):
        """Main polling loop — runs alongside Telegram watcher."""
        log.info("Starting alerts.in.ua polling loop...")
        while True:
            try:
                active = await self.client.get_active_alerts()
                current_ids = set()

                for alert in active:
                    if self.region.lower() not in alert.location_title.lower():
                        continue

                    alert_id = f"{alert.id}_{alert.started_at}"
                    current_ids.add(alert_id)

                    if alert_id not in self.active_alerts:
                        log.info(f"NEW OFFICIAL ALERT: {alert.location_title} — {alert.alert_type}")
                        await self.callback(
                            alert_type=alert.alert_type,
                            location=alert.location_title,
                            started_at=alert.started_at
                        )

                self.active_alerts = current_ids
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                log.error(f"alerts.in.ua polling error: {e}")
                await asyncio.sleep(30)
