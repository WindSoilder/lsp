import socket
from lsp import Connection, NEED_DATA, RequestReceived, DataReceived, MessageEnd

sock = socket.socket()
sock.bind(("0.0.0.0", 10001))
sock.listen(1)
client_sock, addr = sock.accept()
print(f"get connection from {client_sock}")

conn = Connection("server")
try:
    while True:
        while True:
            # call next event to indicate what server socket should do.
            event = conn.next_event()

            # no data coming yet, so the return value is NEED_DATA
            if event is NEED_DATA:
                data = client_sock.recv(1024)
                if data == b"":
                    print("Client connection is closed, I will exit.")
                    exit(0)
                conn.receive(data)
            # Request header is coming :)
            elif isinstance(event, RequestReceived):
                print("Receive request header")
                print(event.to_data())
            # Request data is coming :)
            elif isinstance(event, DataReceived):
                print("Receive request data")
                print(event.to_data())
            # client has send data completely.
            elif isinstance(event, MessageEnd):
                print("Data receive complete:)")
                break

        # so we can call con.get_received_data to fetch what client send.
        received_data = conn.get_received_data()
        print(f"Receiving data: {received_data}")

        # send response back to client.
        print(f"Sending response to client")
        data = conn.send_json({"Content": "I am received:)"})
        client_sock.sendall(data)
        print(f"For now, go to next circle")

        # then we need to call go_next_circle, to get another request from client.
        conn.go_next_circle()
finally:
    sock.close()
