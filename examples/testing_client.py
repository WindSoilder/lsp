import socket
from lsp import Connection, NEED_DATA, DataReceived, MessageEnd

sock = socket.socket()

sock.connect(("localhost", 10001))
conn = Connection("client")


answer = input("Send request?(y/n)")
while answer == "y":
    # use connection send_json method to convert json object to bytes
    request_data = conn.send_json({"method": "didOpen"})
    # then we can send data to server
    sock.sendall(request_data)

    while True:
        # and then we can get next_event of connection, it can indicate
        # that what should we do.
        event = conn.next_event()
        # we need to receive data from server
        if event is NEED_DATA:
            try:
                data = sock.recv(1024)
            except ConnectionResetError:
                print('The server connection is closed, So I will leave:)')
                conn.close()
                sock.close()
                exit(0)
            else:
                print("return from sock.recv")
                conn.receive(data)
        # we have receive data from server
        elif isinstance(event, DataReceived):
            print("Receive event, content:")
            print(event)
        elif isinstance(event, MessageEnd):
            print("Server sending data complete.")
            break

    # then we can call get_received_data() to extract out what we get
    header, response_body = conn.get_received_data()
    print("Response header from server:")
    print(header)
    print("Response body from server:")
    print(response_body)
    answer = input("Send request?(y/n)")
    conn.go_next_circle()
