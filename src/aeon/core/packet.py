import json
import uuid
import time
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class PacketType(str, Enum):
    HANDSHAKE = "handshake"
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"

class PacketHeader(BaseModel):
    packet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    version: str = "1.0.0"
    packet_type: PacketType

class Packet(BaseModel):
    """
    L1 Layer: Structured Communication Packet.
    Replaces raw text communication between agents with a formal protocol.
    """
    header: PacketHeader
    payload: Dict[str, Any]
    signature: Optional[str] = None

    def serialize(self) -> str:
        """Serializes the packet to JSON."""
        return self.model_dump_json()

    @classmethod
    def deserialize(cls, data: str) -> "Packet":
        """Deserializes a JSON string into a Packet."""
        return cls.model_validate_json(data)

    @classmethod
    def create_request(cls, sender: str, receiver: str, activity: str, params: Dict[str, Any]) -> "Packet":
        header = PacketHeader(sender_id=sender, receiver_id=receiver, packet_type=PacketType.REQUEST)
        payload = {"activity": activity, "params": params}
        return cls(header=header, payload=payload)

    @classmethod
    def create_response(cls, sender: str, receiver: str, request_id: str, data: Dict[str, Any]) -> "Packet":
        header = PacketHeader(sender_id=sender, receiver_id=receiver, packet_type=PacketType.RESPONSE)
        payload = {"request_id": request_id, "data": data}
        return cls(header=header, payload=payload)
