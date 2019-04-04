LSP - Language server protocol in Sans-IO pattern
=================================================

Language Server Protocol implementation in sans-io pattern.  Which is highly inspired by `Sans-IO pattern <https://sans-io.readthedocs.io/how-to-sans-io.html>`_.  And some relatived projects:
- `hyper-h2 <https://github.com/python-hyper/hyper-h2>`_
- `h11 <https://github.com/python-hyper/h11>`_

So it can be integreted with trio, asyncio, or some other frameworks easily.

Required python version
-----------------------
Python >= 3.6

Features
--------
1. Pure python implementation
2. Don't relatived to other site-packages
3. Can (should) easily integreted with high level framework like trio, asyncio

How to install it
-----------------
There are two ways to install *lsp*

- Install via *pip* (recommended)

.. code-block:: text

    pip install lsp

- Install via *setup.py*

.. code-block:: shell

    python setup.py install

Basic Usage example
-------------------

Client side
~~~~~~~~~~~

.. code-block:: python

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

Server side
~~~~~~~~~~~

.. code-block:: python

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

For more usage example, please check out files in *examples/servers* folder.

Main API in lsp
---------------
1. Want to send json data?  You can try :code:`conn.send_json`.
2. Want to know what we should do next?  You can try :code:`conn.next_event`.
3. After receive data, please don't forget to call :code:`conn.receive(data)`.
   Which will save data into inner buffer, and it can drive
   :code:`conn.next_event` method returns other events.
4. When Receive :code:`MessageEnd` event, we can just call
   :code:`conn.get_received_data` to fetch for incoming data.

Main events we will get from next_event
---------------------------------------
Client
~~~~~~
Client side will get the following values from next_events:

1. *NEED_DATA* - which indicate that we need to receive data from server.
2. *ResponseReceived* - Client have receive response header.
3. *DataReceived* - Client have receive resposne body.
4. *MessageEnd* - Receive data from server complete.

Server
~~~~~~
Server side will get the following values from next_events:

1. *NEED_DATA* - which indicate that we need to receive data from client.
2. *RequestReceived* - Client have send request header,  and we receive it.
3. *DataReceived* - Server have receive response body from client.
4. *MessageEnd* - Client sending request complete.
