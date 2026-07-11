import socket


HOST = "0.0.0.0"
# HOST = "192.168.31.128"
PORT = 25564


def run():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))
    server.listen()

    print(f"Relay listening on {HOST}:{PORT}")

    while True:
        client, addr = server.accept()

        print(f"Connection from {addr}")

        # client.close()
        data = client.recv(1024)
        print(f"Data: {data}")
        
        from relay_APP.minecraft_protocol import parse_handshake
        try:
            handshake = parse_handshake(data)

            print("=== Minecraft Handshake ===")
            print(f"UUID        : {handshake.server_uuid}")
            print(f"Protocol    : {handshake.protocol_version}")
            print(f"Hostname    : {handshake.hostname}")
            print(f"Relay Port  : {handshake.port}")
            print(f"State       : {handshake.next_state}")

            from core_APP.models import MinecraftServer
            server = MinecraftServer.objects.get(
                server_uuid=handshake.server_uuid,
            )
            print(f"Server Port : {server.port}")

        except Exception as e:
            print("Failed to parse:", e)