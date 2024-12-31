var express = require("express"),
    app = express(),
    server = require("http").createServer(app),
    fileUpload = require('express-fileupload'),
    pageGen = require("./PageGen"),
    servio = require("socket.io")(server),
    MidiConvert = require("./MidiConvert"),
    dan = require("./DAN").dan,
    msgHandler = require("./MessageHandler").msgHandler,
    mboxctlHandler = require("./MBoxCtlHandler").mboxctlHandler,
    ODFList = require("./ShareVariables").ODFList,
    IDFList = require("./ShareVariables").IDFList;

var iottalkIP = process.argv[2];

console.log(iottalkIP);

app.use(express.static("./webapp"));
app.use(fileUpload());

app.get("/", function (req, res) {
    pageGen.Page.getMusicBoxPage(req,res,msgHandler.getC());
});

app.get("/mboxctl|smboxctl", function (req, res) {
    pageGen.Page.getMBoxCtlPage(req,res,iottalkIP,IDFList,
        msgHandler.getCtlDefaultValues());
});
app.get("/management",function (req,res) {
    pageGen.Page.getManagementPage(req,res);
});
app.post('/upload', function(req, res) {
    var sampleFile;
    if (!req.files) {
        res.send('No files were uploaded.');
        return;
    }
    sampleFile = req.files.sampleFile;
    sampleFile.mv("./webapp/midi/"+sampleFile.name, function(err) {
        if (err) {
            res.status(500).send(err);
        }
        else {
            res.send('File uploaded!');
        }
    });
});

msgHandler.setSocketIo(servio);
mboxctlHandler.setSocketIo(servio);

server.listen((process.env.PORT || 5566), '0.0.0.0');

var genMacAddr = function () {
    var addr = '';
    for (var i = 0; i < 5; i++)
        addr += '0123456789abcdef'[Math.floor(Math.random() * 16)];
    return addr;
};
var macAddr = genMacAddr();
console.log('mac address:' + macAddr);
dan.init(msgHandler.pull, 'http://' + iottalkIP , macAddr, {

    'dm_name': 'MusicBox',
    'd_name' : (Math.floor(Math.random() * 99)).toString() +'.'+ "MusicBox",
    'u_name': 'yb',
    'is_sim': false,
    'df_list':ODFList

}, function (result) {
    console.log('register:', result);

    //deregister when app is closing
    process.on('exit', dan.deregister);
    //catches ctrl+c event
    process.on('SIGINT', dan.deregister);
    //catches uncaught exceptions
    process.on('uncaughtException', dan.deregister);

});









