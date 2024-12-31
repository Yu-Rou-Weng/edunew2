var fs = require('fs'),
    ejs = require('ejs'),
    color = require('./ShareVariables').color,
    musicBoxDir = __dirname + "/webapp/html/MusicBox.ejs",
    mBoxCtlDir = __dirname + "/webapp/html/MBoxCtl.ejs",
    managementDir = __dirname + "/webapp/html/Management.ejs",
    midiDir = __dirname + "/webapp/midi";

var Page = function () {};

Page.prototype = {
    getMusicBoxPage : function (req, res, speakerNum) {

        fs.readFile(musicBoxDir,
            function (err, contents) {
                if (err) {
                    console.log(err);
                }
                else {
                    contents = contents.toString('utf8');
                    res.writeHead(200, {"Content-Type": "text/html"});
                    var columnNum = 3;
                    var tr = [];
                    var colorIndex = 0;
                    for (var i = 0; i < Math.ceil(speakerNum / columnNum); i++) {
                        var td = [];
                        for (var j = 0; j < columnNum; j++) {
                            if (colorIndex < speakerNum)
                                td.push(color[colorIndex++]);
                        }
                        tr.push(td);
                    }
                    // console.log({tr:tr,space:space});
                    res.end(ejs.render(contents, {tr: tr}));
                }
            }
        );
    },
    getMBoxCtlPage : function (req, res, iottalkIP,IDFList, ctlDefaultValues) {

        readAllSongInDir(midiDir, function (err, songNames) {
            if (err)
                console.log(err);
            else {
                fs.readFile(mBoxCtlDir,
                    function (err, contents) {
                        if (err) {
                            console.log(err);
                        }
                        else {
                            var displaySongNames = [];
                            for(var i = 0; i < songNames.length; i++)
                                displaySongNames.push(songNames[i].replace(/_/g, " "));
                            var songs = {
                                songNames:songNames,
                                displaySongNames:displaySongNames
                            };
                            contents = contents.toString('utf8');
                            res.writeHead(200, {"Content-Type": "text/html"});
                            res.end(ejs.render(contents, {
                                songs: songs,
                                iottalkIP: iottalkIP,
                                IDFList: IDFList,
                                ctlDefaultValues: ctlDefaultValues
                            }));
                        }
                    }
                );
            }

        });
    },
    getManagementPage : function (req,res) {
        fs.readFile(managementDir,
            function (err, contents) {
                if (err) {
                    console.log(err);
                }
                else {
                    contents = contents.toString('utf8');
                    res.writeHead(200, {"Content-Type": "text/html"});
                    res.end(ejs.render(contents));
                }
            }
        );
    }
};


var readAllSongInDir = function (midiDir, callback) {
    fs.readdir(midiDir, function (err, files) {
        if (err) {
            callback(err);
            return;
        }
        else {
            var songs = [];
            for (var i = 0; i < files.length; i++) {
                var l = files[i].length;
                if (files[i].slice(l - 3, l).toLowerCase() == "mid")
                    songs.push(files[i].slice(0, l - 4));
            }
            callback(null, songs);
        }
    });
};


exports.Page = new Page();