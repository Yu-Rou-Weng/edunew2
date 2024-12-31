var color = require('./ShareVariables').color;

var msgHandler = (function () {

    var song = null,
        rawSong = null,
        songId = -1,
        playing = false,
        repeatSong = false,
        head = 0,
        period = 20,
        volume  = 0,
        room = 0,
        C = 7,
        N = 5,
        luminance = 1.0,
        key = 0,
        mode = 0,
        space = Array.apply(null, Array(color.length)).map(Number.prototype.valueOf,N),
        servio = null;

    var partition = function (len) {
        var r;
        if (head < len) {
            if (head + period < len) {
                r = {"start": head, "end": head + period};
                head += period;
            }
            else {
                r = {"start": head, "end": len};
                head = len;
            }
            // console.log(r);
            return r;
        }
        else {
            return null;
        }
    };
    var sendNotes = function () {

        if( !seekRoom() ){
            console.log('all exit');
            return
        }

        // find all iOS socket connection and send light signal without songPart,
        // because iOS is not support tonejs
        for(var i = 0; i < iOSClient.length; i++){
            if(iOSClient[i].room == (room%C)){
                servio.to(iOSClient[i].id).emit('L-O',1);
            }
        }
        if (song != null){
            //reset MusicBox page volume and key
            sendFeature("Volume-O",volume);
            sendFeature("Key-O",0);

            var part = song.songPart;
            var r = partition(part.length);
            if (r != null) {
                var p = part.slice(r.start, r.end);
                addNoteToSongEnd(p);
                var o = {songPart: p};
                servio.sockets.in(room % C).emit('Song-O', o);
                room++;
                playing = true;
            }
            else {
                reset();
                console.log('reset');
            }
        }

    };
    var sendSong = function () {

        // find all iOS socket connection and send light signal without songPart,
        // because iOS is not support tonejs
        // for(var i = 0; i < iOSClient.length; i++)
        //     servio.to(iOSClient[i].id).emit('L-O',1);
        head = song.songPart.length;
        addNoteToSongEnd(song.songPart);
        for(var i = 0; i < C; i++){

            if(N-space[i] > 0){
                var scale = Math.ceil(i/2);

                if(i%2) {
                    sendFeature('Key-O', scale*-1, i);
                    sendFeature('Volume-O', scale*2, i);
                }
                else {
                    sendFeature('Key-O', scale, i);
                    sendFeature('Volume-O',scale*-2,i);
                }
                servio.sockets.in(i).emit('Song-O', {songPart:song.songPart,mode:1});
            }
        }

    };
    var reset = function () {
        playing = false;
        head = 0;
        room = 0;
        song = null;
        servio.sockets.emit("mute",false);
    };
    var addIndexToSongPart = function(part){
        //add unique id for each note in part
        for (var i = 1; i <= part.length; i++)
            part[i-1].index = i;
    };
    var addNoteToSongEnd = function (part) {
        var j = part.length-1;
        for(var i = part.length-2; i >= 0 ; i--){
            if(part[j].time != part[i].time)
                break;
        }
        var max = -1;
        for(var k = i; k <= j; k++){
            var t = parseInt(part[k].time)+parseInt(part[k].duration);
            max = (t > max) ? t : max;
        }
        var lastNote = {duration: '10i',time: max+"i",noteName: 'A3',index:-1};
        part.push(lastNote);
    };
    var seekRoom = function () {
        //seek for non-empty room
        for(var i = 0; i < C; i++){
            room += i;
            if(N-space[room%C] > 0){// none empty
                if(N-space[room%C] == 1)
                    servio.sockets.in(room%C).emit("mute",false);
                break;
            }
        }
        if(i == C)
            return false;
        else
            return true;
    };
    var sendFeature = function(feature,obj,room){
        if(room != undefined)
            servio.sockets.in(room).emit(feature,obj);
        else
            servio.sockets.emit(feature, obj);
    };
    var iOSClient = [];
    var receiveSongAckNum = 0;
    return {
        setSocketIo:function (io) {
            servio = io;
            servio.sockets.on('connection', function (socket) {

                //update space for MusicBox page
                socket.on('initSpace',function () {
                    servio.sockets.emit('changeSpace',space);
                });
                socket.on('join', function (room) {
                    if(playing){
                        servio.to(socket.id).emit("mute",true);
                    }
                    if(space[room] > 0) {
                        socket.join(room);
                        space[room]--;
                        space[room] = (space[room] < 0)? 0 : space[room];
                        servio.sockets.emit('changeSpace',space);
                        servio.to(socket.id).emit("join", {message:"approve",room:room});
                        servio.sockets.in(room).emit("counter",N-space[room]);
                    }
                    else
                        servio.to(socket.id).emit("join",{message:"disapprove"});

                });
                socket.on('join_iOS',function (room) {
                    if(space[room] > 0) {
                        //iOS is not support tonejs so manage iOS socket in other way
                        socket.room = room;
                        socket.iOS = true;
                        iOSClient.push(socket);
                        servio.to(socket.id).emit("join", {message:"approve",room:room});
                    }
                    else
                        servio.to(socket.id).emit("join",{message:"disapprove"});
                });
                //track musicbox playing message
                var playMsg = null;
                socket.on('playMsg',function (msg) {
                    playMsg = msg;
                });

                var findClientsSocketByRoomId = function(roomId) {
                    var roomId = roomId.toString();
                    var rooms = Object.keys(io.sockets.adapter.rooms);

                    if(rooms.indexOf(roomId) != -1)
                        return io.sockets.adapter.rooms[roomId];

                    return null;
                };
                var findSocketRoom = function(socket)  {
                    for(var i = 0; i < color.length; i++){
                        if(findClientsSocketByRoomId(i) != null) {
                            var clients = findClientsSocketByRoomId(i)['sockets'];
                            var clientsId = Object.keys(clients);
                            if(clientsId.indexOf(socket.id) != -1)
                                return i;
                        }
                    }
                    return -1;
                };
                //close window
                socket.onclose = function(reason) {
                    var room;
                    if(socket.iOS) {
                        room = socket.room;
                        if(room == undefined)
                            return;
                        //remove iOS socket from iOSClient array
                        var index = iOSClient.indexOf(socket);
                        if (index > -1)
                            iOSClient.splice(index, 1);
                    }
                    else{
                        room = findSocketRoom(socket);
                        if(room == -1)
                            return;
                        socket.leave(room);
                        space[room]++;
                        space[room] = (space[room] > N)? N : space[room];
                        servio.sockets.emit('changeSpace',space);
                        servio.sockets.in(room).emit("counter",N-space[room]);
                        if(mode == 0) {

                            //if only one socket in room mute = false
                            if ((N - space[room]) == 1)
                                servio.sockets.in(room).emit("mute", false);

                            //leave when playing and there is not other speaker playing in this room
                            if (playMsg != null && playMsg.room == room
                                && playMsg.state == "started" && (N - space[room]) == 0) {
                                head = playMsg.noteIndex - 1;
                                sendNotes();
                            }
                        }
                    }
                    Object.getPrototypeOf(this).onclose.call(this, reason);
                };

                socket.on('partEndAck', function (ackRoomLastNoteIndex) {

                    //make iOS MusicBox dark if there are some sockets light last turn.
                    for(var i = 0; i < iOSClient.length; i++)
                        servio.to(iOSClient[i].id).emit("L-O",0);
                    //repeatSong for mode 0
                    if(repeatSong && mode == 0 && head == song.songPart.length ) {
                        reset();
                        servio.sockets.emit("switchSong");
                        song = JSON.parse(JSON.stringify(rawSong));
                        addIndexToSongPart(song.songPart);
                        sendNotes();
                        console.log('repeat');
                        return;
                    }
                    //repeatSong for mode 1
                    if(repeatSong && mode == 1 && head == song.songPart.length-1) {
                        reset();
                        servio.sockets.emit("switchSong");
                        song = JSON.parse(JSON.stringify(rawSong));
                        addIndexToSongPart(song.songPart);
                        sendSong();
                        console.log('repeat');
                        return;
                    }
                    //partEndAck for mode 0
                    if(mode == 0 && ackRoomLastNoteIndex == head)
                        sendNotes();

                });

                socket.on('receivePlayMode1Ack',function () {
                    //calculate established socket number
                    receiveSongAckNum++;
                    var socketNum = 0;
                    for(var i = 0; i < C; i++)
                        socketNum += N-space[i];
                    if(receiveSongAckNum == socketNum) {
                        servio.sockets.emit('playMode1');
                        receiveSongAckNum = 0;
                    }
                });

            });
        },
        pull:function (odf_name, data) {

            console.log( odf_name+":"+ data );
            var obj = data[0];

            switch (odf_name){
                case "Song-O":
                    reset();
                    song = obj;
                    // copy obj by using JSON parse and stringify
                    song = JSON.parse(JSON.stringify(obj));
                    // rawSong will be used when replay the song
                    rawSong = JSON.parse(JSON.stringify(obj));

                    if (songId != -1) {
                        console.log("switch song!");
                        servio.sockets.emit("switchSong");
                    }
                    songId = song.songId;
                    addIndexToSongPart(song.songPart);
                    if(mode == 0)
                        sendNotes();
                    else if(mode == 1)
                        sendSong();

                    break;
                case "Key-O":
                    sendFeature(odf_name,obj);
                    key = parseInt(obj);
                    break;
                case "Volume-O":
                    sendFeature(odf_name,obj);
                    volume = parseInt(obj);
                    break;
                case "L-O":
                    sendFeature(odf_name,obj);
                    luminance = parseInt(obj);
                    break;
                case "Period-O":
                    period = parseInt(obj);
                    break;
                case "C-O":
                    C = parseInt(obj);
                    break;
                case "N-O":
                    N = parseInt(obj);
                    space = Array.apply(null, Array(color.length)).map(Number.prototype.valueOf,N)
                    break;
                case "Mode-O":
                    mode = parseInt(obj);
                    break;
            }
        },
        getC:function () {
            return C;
        },
        getCtlDefaultValues:function () {
            var modeName;
            if(mode == 0)
                modeName = "sequential";
            else if(mode == 1)
                modeName = "parallel";
            return  {
                C:C,
                N:N,
                Mode:modeName,
                Period:period,
                L:luminance,
                Key:key,
                Volume:volume
            };
        },
        setRepeatSong:function (r) {
            repeatSong = Boolean(r);
        }
    };
})();

exports.msgHandler = msgHandler;


