import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class DetectionConsumer(AsyncWebsocketConsumer):
    group_name = "detections"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug("ws_connected | channel=%s", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("ws_disconnected | channel=%s code=%s", self.channel_name, close_code)

    async def receive(self, text_data=None, bytes_data=None):
        # Dashboard is read-only; clients should not send data.
        logger.debug(
            "ws_unexpected_message | channel=%s text_len=%s bytes_len=%s",
            self.channel_name,
            len(text_data) if text_data else 0,
            len(bytes_data) if bytes_data else 0,
        )

    async def detection_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))
