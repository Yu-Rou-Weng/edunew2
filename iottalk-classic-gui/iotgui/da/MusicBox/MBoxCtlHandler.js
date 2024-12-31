var csmapi = require("./CSMAPI").csmapi;
var msgHandler = require("./MessageHandler").msgHandler;
var servio = null;
//map socket id and mac
var mboxctlDict = {};
var smboxctlCount = 0;


var smboxctlPlayerControls = {
    state:"play",
    repeatSong:false,
    songId:-1
};

var mboxctlHandler = (function () {
    return {
        setSocketIo: function (io) {
            servio = io;
            servio.sockets.on('connection', function (socket) {
                socket.on('mboxctlMacAddr',function (mac) {
                    mboxctlDict[socket.id] = mac;
                    if(mac == "Share")
                        smboxctlCount++;
                    socket.onclose = function(reason) {
                        if(mboxctlDict[socket.id] == "Share"){
                            smboxctlCount--;
                            if(smboxctlCount != 0)
                                return;
                        }
                        csmapi.deregister(mboxctlDict[socket.id],function () {
                            servio.sockets.emit("pause");
                            console.log("mboxctl: deregister");
                        });
                        delete mboxctlDict[socket.id];
                        Object.getPrototypeOf(this).onclose.call(this, reason);
                    };

                });
                socket.on('ctl',function(cmd){
                    switch(cmd.name){
                        case "pause":
                            if(mboxctlDict[socket.id] == "Share")
                                smboxctlPlayerControls.state = "pause";
                            console.log("pause");
                            servio.sockets.emit("pause");
                            break;
                        case "play":
                            if(mboxctlDict[socket.id] == "Share")
                                smboxctlPlayerControls.state = "play";
                            console.log("play");
                            servio.sockets.emit("play");
                            break;
                        case "repeatSong":
                            if(mboxctlDict[socket.id] == "Share")
                                smboxctlPlayerControls.repeatSong = cmd.value;
                            msgHandler.setRepeatSong(cmd.value);
                            console.log("repeatSong: " + cmd.value);
                            break;
                        case "chooseSong":
                            if(mboxctlDict[socket.id] == "Share")
                                smboxctlPlayerControls.songId = cmd.value;
                            console.log("chooseSong: " + cmd.value);
                            break;
                    }
                    if(mboxctlDict[socket.id] == "Share"){
                        var keys = Object.keys(mboxctlDict);
                        for(var i = 0; i < keys.length; i++){
                            if(mboxctlDict[keys[i]] == "Share" && keys[i] != socket.id)
                                servio.to(keys[i]).emit("setPlayerControls",smboxctlPlayerControls);
                        }
                    }
                });
                socket.on("getPlayerControls",function () {
                    servio.to(socket.id).emit("setPlayerControls",smboxctlPlayerControls);
                });

            });
        }
    }
})();

exports.mboxctlHandler = mboxctlHandler;
