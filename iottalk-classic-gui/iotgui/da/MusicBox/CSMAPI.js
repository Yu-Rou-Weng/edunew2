var http = require('http');
var csmapi = (function () {
    var ENDPOINT;
    function set_endpoint (endpoint) {
        ENDPOINT = endpoint.slice(7,endpoint.length-5);
    }

    function get_endpoint () {
        return ENDPOINT;
    }

    function register (mac_addr, profile, callback) {
        // $.ajax({
        //     type: 'POST',
        //     url: ENDPOINT +'/'+ mac_addr,
        //     data: JSON.stringify({'profile': profile}),
        //     contentType:"application/json; charset=utf-8",
        // }).done(function () {
        //     if (callback) {
        //         callback(true);
        //     }
        // }).fail(function () {
        //     if (callback) {
        //         callback(false);
        //     }
        // });
        var data = JSON.stringify({'profile': profile});
        var options = {
            host: ENDPOINT,
            port: 9999,
            path:  '/'+ mac_addr,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': data.length
            }
        };
        var req = http.request(options, function(res) {
            if (callback) {
                callback(true);
            }
        });
        req.write(data);
        req.end();
    }

    function deregister (mac_addr, callback) {
        // $.ajax({
        //     type: 'DELETE',
        //     url: ENDPOINT +'/'+ mac_addr,
        //     contentType:"application/json; charset=utf-8",
        // }).done(function () {
        //     if (callback) {
        //         callback(true);
        //     }
        // }).fail(function () {
        //     if (callback) {
        //         callback(false);
        //     }
        // });
        var options = {
            host: ENDPOINT,
            port: 9999,
            path:  '/'+ mac_addr,
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
            }
        };
        var req = http.request(options, function(res) {
            if (callback) {
                callback(true);
            }
        });
        req.end();
    }

    function pull (mac_addr, odf_name, callback) {
        // $.ajax({
        //     type: 'GET',
        //     url: ENDPOINT +'/'+ mac_addr +'/'+ odf_name,
        //     contentType:"application/json; charset=utf-8",
        // }).done(function (obj) {
        //     if (typeof obj === 'string') {
        //         obj = JSON.parse(obj);
        //     }
        //
        //     if (callback) {
        //         callback(obj['samples']);
        //     }
        // }).fail(function () {
        //     if (callback) {
        //         callback([]);
        //     }
        // });
        var options = {
            host: ENDPOINT,
            port: 9999,
            path:  '/'+ mac_addr+'/'+odf_name,
            method: 'GET',
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
            }
        };
        var req = http.request(options, function(res) {
            res.setEncoding('utf8');
            var obj = '';
            res.on('data', function(chunk){
                obj += chunk;
            });
            res.on('end', function () {
                if (typeof obj === 'string') {
                    obj = JSON.parse(obj);
                }
                if (callback) {
                    callback(obj['samples']);
                }
            });

        });
        req.end();
    }

    function push (mac_addr, idf_name, data, callback) {
        // $.ajax({
        //     type: 'PUT',
        //     url: ENDPOINT +'/'+ mac_addr +'/'+ idf_name,
        //     data: JSON.stringify({'data': data}),
        //     contentType:"application/json; charset=utf-8",
        // }).done(function () {
        //     if (callback) {
        //         callback(true);
        //     }
        // }).fail(function () {
        //     if (callback) {
        //         callback(false);
        //     }
        // });
        var options = {
            host: ENDPOINT,
            port: 9999,
            path:  '/'+ mac_addr+'/'+idf_name,
            method: 'PUT',
            data:JSON.stringify({'data': data}),
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': data.length
            }
        };
        var req = http.request(options, function(res) {
            if (callback) {
                callback(true);
            }
        });
        req.write(data);
        req.end();
    }

    return {
        'set_endpoint': set_endpoint,
        'get_endpoint': get_endpoint,
        'register': register,
        'deregister': deregister,
        'pull': pull,
        'push': push,
    };
})();

exports.csmapi = csmapi;