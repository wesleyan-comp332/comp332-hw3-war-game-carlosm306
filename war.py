"""
war card game client and server
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import socket
import socketserver
import threading
import sys


"""
Namedtuples work like classes, but are much more lightweight so they end
up being faster. It would be a good idea to keep objects in each of these
for each game which contain the game's state, for instance things like the
socket, the cards given, the cards still available, etc.
"""
Game = namedtuple("Game", ["p1", "p2"])

# Stores the clients waiting to get connected to other clients
global waiting_clients
waiting_clients = []


"""
I would like to use 2 late days for this assignment

"""

class Command(Enum):
    """
    The byte values sent as the first byte of any message in the war protocol.
    """
    WANTGAME = 0
    GAMESTART = 1
    PLAYCARD = 2
    PLAYRESULT = 3


class Result(Enum):
    """
    The byte values sent as the payload byte of a PLAYRESULT message.
    """
    WIN = 0
    DRAW = 1
    LOSE = 2


async def handle_clients(reader, writer):
    data = await reader.readexactly(2)
    """
    if kill_game(data) == True:
        writer.close()
        await writer.wait_closed()
        return
    """
    if data != bytes([Command.WANTGAME.value, Command.WANTGAME.value]):
        writer.close()
        await writer.wait_closed()
        return 
    

    waiting_clients.append((reader, writer))

    if len(waiting_clients) < 2:
        return

    reader1, writer1 = waiting_clients.pop(0)
    reader2, writer2 = waiting_clients.pop(0)

    try:
        firsthalf, secondhalf = deal_cards()
        writer1.write(bytes([Command.GAMESTART.value]+ firsthalf))
        writer2.write(bytes([Command.GAMESTART.value] + secondhalf))
        await writer1.drain()
        await writer2.drain()

        

        for i in range(26):
            data1 = await reader1.readexactly(2)
            data2 = await reader2.readexactly(2)

            if data1[0] != Command.PLAYCARD.value or data2[0] != Command.PLAYCARD.value:
                break

            card1 = data1[1]
            card2 = data2[1]
            result = compare_cards(card1, card2)

            if result == 1:
                res1, res2 = Result.WIN.value, Result.LOSE.value
            elif result == -1:
                res1, res2 = Result.LOSE.value, Result.WIN.value
            else:
                res1 = res2 = Result.DRAW.value

            writer1.write(bytes([Command.PLAYRESULT.value, res1]))
            writer2.write(bytes([Command.PLAYRESULT.value, res2]))
            await writer1.drain()
            await writer2.drain()

    except Exception as e:
        print(f"Error during game: {e}")
        
    finally:
        writer1.close()
        writer2.close()
        await writer1.wait_closed()
        await writer2.wait_closed()

            
          
#apparently there is a built in function on asyncio with the same name, so I didn't use this one
def readexactly(sock, numbytes):
    """
    Accumulate exactly `numbytes` from `sock` and return those. If EOF is found
    before numbytes have been received, be sure to account for that here or in
    the caller.
    """
    data = b''
    while len(data) < numbytes:
        try:
            remaining_bytes = numbytes - len(data)
            chunk = sock.recv(remaining_bytes)
            if not chunk:
                return None
            data += chunk
        except socket.error as e:
            print(f"Socket error: {e}")
            return None
    return data


def kill_game(game):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    if game[0] == 0 or game[0] == 1 or game[0] == 2 or game[0] == 3:
        pass
    if game[1] == 0 or game[1] == 1 or game[1] == 2 or game[1] == 3:
        pass
    else:
        print("bad numbers")
        return True

    """
    message = game[1][1]
    array = [WANTGAME, GAMESTART, PLAYCARD, PLAYRESULT]
    i = 0
    while i < 4:
        if message == array[i]:
            return None
        i +=1
    connection.close()
    return None

    """

kill_game([4,3])

def compare_cards(card1, card2):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    """
    numbers = list(range(52))
    
    vals = list(range(13))* 4
    
    my_dict = dict(zip(numbers, vals))

    firstcard = my_dict[card1]
    secondcard = my_dict[card2]

    if (firstcard == secondcard):
        return 0
    if (firstcard > secondcard):
        return 1
    if (firstcard < secondcard):
        return -1
    

def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    numbers = list(range(52))
    
    random.shuffle(numbers)
    
    middle = len(numbers)//2
    
    firsthalf = numbers[:middle]
    
    secondhalf = numbers[middle:]

    deck = (firsthalf, secondhalf)

    return deck

#deal_cards()
    

def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    serverloop = asyncio.new_event_loop()
    asyncio.set_event_loop(serverloop)
    server = asyncio.start_server(handle_clients, host, port)
    serverloop.run_until_complete(server)
    
    try:
        serverloop.run_forever()
    except KeyboardInterrupt:
        print("server shutting down")
        server.close()
        serverloop.close()


async def limit_client(host, port, loop, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port, loop)

async def client(host, port, loop):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "drew"
        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

def main(args):
    """
    launch a client/server
    """
    host = args[1]
    port = int(args[2])
    if args[0] == "server":
        try:
            # your server should serve clients until the user presses ctrl+c
            serve_game(host, port)
        except KeyboardInterrupt:
            print("Server stopped")
        return
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(loop)
        
    if args[0] == "client":
        loop.run_until_complete(client(host, port, loop))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, loop, sem)
                   for x in range(num_clients)]
        async def run_all_clients():
            """
            use `as_completed` to spawn all clients simultaneously
            and collect their results in arbitrary order.
            """
            completed_clients = 0
            for client_result in asyncio.as_completed(clients):
                completed_clients += await client_result
            return completed_clients
        res = loop.run_until_complete(
            asyncio.Task(run_all_clients(), loop=loop))
        logging.info("%d completed clients", res)

    loop.close()


if __name__ == "__main__":
    # Changing logging to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])

