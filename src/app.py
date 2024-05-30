from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase


# config.
app = Flask(__name__)
app.config["SECRET_KEY"] = "flask_secret_key_shhhh" # keep this secret in production
socketio = SocketIO(app)

rooms = {}

def get_room_code(length):
    """
    The get_room_code function generates a random room code of length `length` that is not already in use.
    
    :param length: Determine the length of the room code
    :return: A random code of len = length
    """
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    """
    The home function is the main function that handles all of the logic for
    the home page. Handles both creating and joining rooms, as well as
    displaying any errors that may occur during this process.
    
    :return: A render_template call
    """

    session.clear()
    if request.method == "POST":

        # retrieve request params
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # No name entered
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        # No room code entered
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        # create a new room
        room = code
        if create != False:
            room = get_room_code(5)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    # get the room from a previous session, if any
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        #redirect to home if no session found
        return redirect(url_for("home"))
    
    return render_template("chatroom.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    """
    The message function is called when a user sends a message to the chatroom.
    It takes in the data sent by the client, and then uses that data to create 
    a dictionary containing both their name and what they said. It then sends this 
    dictionary back out to all clients connected to that room, using send(). Finally, it appends this same dictionary into an array of messages for that room.
    
    :param data: Get the data from the client
    :return: The message to the client
    """
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    """
    The connect function is called when a client connects to the server.
    It will add the client to a room and broadcast that they have entered it.
    
    :param auth: Authenticate the user
    :return: Nothing
    """
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    """
    The disconnect function is called when a user leaves the room.
    It removes the user from the room and sends a message to all users in that room
    that this particular user has left.
    """
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1

        # delete room if there are no members
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    # user has left the room
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")