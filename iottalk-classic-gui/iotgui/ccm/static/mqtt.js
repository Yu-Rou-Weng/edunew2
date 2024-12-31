function mqtt_init() {
  let url = window.location.origin + '/iottalk/ccm/mqtt_url';
  $.getJSON(url)
    .done((data) => {
      let mqtt_id = data.id;
      let scheme = data.ws_scheme;
      let host = data.host;
      let socket = data.ws_port;
      let username = data.username || '';
      let password = data.password || '';
      let req = "iottalk/api/gui/req/" + mqtt_id;
      let res = "iottalk/api/gui/res/" + mqtt_id;
      // Store the credential ID into the session storage
      window.sessionStorage.setItem('credential_id', data.credential_id)
      mqtt_client.connect(scheme, mqtt_id, host, socket, username, password, req, res,
        window['mqtt_connect_callback'],
        window['anno_callback']);
    })
    .fail(() => {
      alert('Can not connect to MQTT broker, please try again later');
    });
}

function UUID () {
  function s4() {
    return Math.floor((1 + Math.random()) * 0x10000)
      .toString(16)
      .substring(1);
  }
  return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
    s4() + '-' + s4() + s4() + s4();
}

var mqtt_client = (function() {
  var _mqtt_client;
  var _mqtt_scheme;
  var _mqtt_host;
  var _mqtt_port;
  let _mqtt_username;
  let _mqtt_password;
  var _mqtt_id;
  var _mqtt_req_topic;
  var _mqtt_res_topic;
  var _mqtt_connect_callback;
  var _mqtt_anno_callback;
  var _mqtt_topic_callback = {}; // for topic listener
  var _mqtt_callback_list = {}; // for request call back

  function mqtt_message(topic, message, retained=false) {
    let msg = new Paho.MQTT.Message(message);
    msg.destinationName = topic;
    msg.retained = retained;
    return msg;
  }

  function detach_mqtt_message(topic) {
    let flag = UUID();
    let msg = {
      'op': 'detach',
      'flag': flag,
      '_id': _id,
      // Get the credential ID from the session storage
      'data': {'credential_id': window.sessionStorage.getItem('credential_id'), },
    };
    return mqtt_message(topic, JSON.stringify(msg));
  }

  function publish(message, callback, retained=false) {
    console.log('[mqtt publish]: ' + message);
    if (_mqtt_client) {
      _mqtt_client.send(mqtt_message(_mqtt_req_topic, message, retained));
    }
  }

  function request(op, data, callback) {
    let flag = UUID();
    let msg = {
      'op': op,
      'flag': flag,
      'data': data,
      '_id': _id,
      'req_timestamp': (new Date()).getTime(),
    };

    if (callback) {
      _mqtt_callback_list[flag] = callback;
    }

    publish(JSON.stringify(msg), callback);
  }

  function subscribe(topic) {
    if (_mqtt_client) {
      _mqtt_client.subscribe(topic);
    }
  }

  function _subscribe(topic, callback){
    _mqtt_topic_callback[topic] = callback;
    _mqtt_client.subscribe(topic);
  }

  function unsubscribe(topic) {
    if (_mqtt_client) {
      _mqtt_client.unsubscribe(topic);
    }
  }

  function on_connect() {
    if (_mqtt_connect_callback) {
      _mqtt_connect_callback(true);
    }
    subscribe(_mqtt_res_topic);
    request('attach');
    gui_init();
  }

  function on_message(data) {
    let msg = JSON.parse(data.payloadString);

    if (_mqtt_topic_callback[data.destinationName]) {
      _mqtt_topic_callback[data.destinationName](msg);
    }

    if (!('op' in msg)) {
      return;
    }

    else if ('anno' == msg['op']) {
      if ('Authentication Fail' == msg['state']) {
        window.location = window.location.origin + "/iottalk/ccm/login";
      }
      else if (_mqtt_anno_callback) {
        _mqtt_anno_callback(msg);
      }
    }
    else if (!('flag' in msg) && !('state' in msg)) {
      return;
    }
    else if (!('ok' == msg['state'])) {
      if ('error' == msg['state']) {
        alert(msg['msg']);
      }
      return;
    }
    else if ('attach' == msg['op']) {
      return;
    }
    else if (_mqtt_callback_list[msg['flag']]) {
      _mqtt_callback_list[msg['flag']](msg['data']);
      delete _mqtt_callback_list[msg['flag']];
    }
  }

  function on_failure() {
    if (_mqtt_connect_callback) {
      _mqtt_connect_callback(false);
    }
    _mqtt_client = null;
    setTimeout(_connect, 3000);
  }

  function onConnectionLost(responseObject) {
    if (responseObject.errorCode !== 0) {
      console.log("Connection Lost:"+responseObject.errorMessage);
      if (_mqtt_connect_callback) {
        _mqtt_connect_callback(false);
      }
      _mqtt_client = null;
      setTimeout(_connect, 3000);
    }
  }

  function connect(scheme, mqtt_id, host, port, username, password, req_topic, res_topic,
                   conn_callback, anno_callback) {
    _mqtt_scheme = scheme;
    _mqtt_host = host;
    _mqtt_port = port;
    _mqtt_username = username;
    _mqtt_password = password;
    _mqtt_id = mqtt_id;
    _mqtt_req_topic = req_topic;
    _mqtt_res_topic = res_topic;
    _mqtt_connect_callback = conn_callback;
    _mqtt_anno_callback = anno_callback;

    if (!_mqtt_host || !_mqtt_port || !_mqtt_id) {
      console.log('mqtt server info wrong!');
      return;
    }

    if (!_mqtt_req_topic || !_mqtt_res_topic) {
      console.log('mqtt topic wrong!')
      return;
    }

    _connect();
  }

  function _connect() {
    if (!_mqtt_client) {
      _mqtt_client = new Paho.MQTT.Client(_mqtt_host, Number(_mqtt_port), _mqtt_id);
      _mqtt_client.onConnectionLost = onConnectionLost;
      _mqtt_client.onMessageArrived = on_message;
      _mqtt_client.connect({
        'userName': _mqtt_username,
        'password': _mqtt_password,
        'useSSL': (_mqtt_scheme == "wss"),
        'onSuccess': on_connect,
        'onFailure': on_failure,
        'willMessage': detach_mqtt_message(_mqtt_req_topic),
      });
    }
  }

  function status() {
    return !!_mqtt_client;
  }

  return {
    'connect': connect, //connect(host, port, req_topic, res_topic, fail_callback)
    'request': request, //request(op, data, callback), callback(data)
    'status': status, //statu(), return
    'subscribe': _subscribe, // subscribe(topic, callback)
    'unsubscribe': unsubscribe, // unsubscribe(topic)
  };
})();
