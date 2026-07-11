from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class Handshake:
    packet_length: int
    packet_id: int
    protocol_version: int
    hostname: str
    port: int
    next_state: int

    @property
    def server_uuid(self) -> UUID:
        """
        Returns the UUID encoded in the hostname.

        Expected format:

            <uuid>.mcmanager
        """

        labels = self.hostname.split(".")

        if len(labels) != 2:
            raise ValueError(
                f"Invalid hostname '{self.hostname}'"
            )

        if labels[1] != "mcmanager":
            raise ValueError(
                f"Invalid relay domain '{labels[1]}'"
            )

        return UUID(labels[0])


def read_varint(data, offset=0):
    value = 0
    position = 0

    while True:
        if offset >= len(data):
            raise ValueError("Unexpected end of packet while reading VarInt")

        current = data[offset]
        offset += 1

        value |= (current & 0x7F) << (7 * position)

        if (current & 0x80) == 0:
            break

        position += 1

        if position >= 5:
            raise ValueError("VarInt too big")

    return value, offset


def parse_handshake(data):
    packet_length, offset = read_varint(data)

    packet_id, offset = read_varint(data, offset)

    if packet_id != 0:
        raise ValueError(f"Expected handshake packet (0), got {packet_id}")

    protocol_version, offset = read_varint(data, offset)

    host_length, offset = read_varint(data, offset)

    if offset + host_length > len(data):
        raise ValueError("Hostname extends beyond packet")

    hostname = data[offset:offset + host_length].decode("utf-8")
    offset += host_length

    if offset + 2 > len(data):
        raise ValueError("Packet ended before port")

    port = int.from_bytes(data[offset:offset + 2], "big")
    offset += 2

    next_state, offset = read_varint(data, offset)

    state_name = {
        1: "Status",
        2: "Login",
    }.get(next_state, f"Unknown ({next_state})")

    return Handshake(
        packet_length=packet_length,
        packet_id=packet_id,
        protocol_version=protocol_version,
        hostname=hostname,
        port=port,
        next_state=next_state,
    )