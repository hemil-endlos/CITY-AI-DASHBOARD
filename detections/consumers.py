import json

from channels.generic.websocket import AsyncWebsocketConsumer


class DetectionConsumer(AsyncWebsocketConsumer):
    group_name = "detections"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Dashboard is read-only; ignore incoming messages from clients.
        return

    async def detection_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))

