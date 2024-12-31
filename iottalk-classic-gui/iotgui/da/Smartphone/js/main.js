// Use IIFE to avoid the global context pollution
(() => {
  let accuracy = 10;
  let interval = 500;
  const browserInfo = bowser.parse(window.navigator.userAgent);
  const id = uuidv4();
  const acceleration = {x: 0, y: 0, z: 0, };
  const gyroscope = {x: 0, y: 0, z: 0, };
  const orientation = {x: 0, y: 0, z: 0, oc: 0, };
  const AxDom = $('#accelerationX > div > span');
  const AyDom = $('#accelerationY > div > span');
  const AzDom = $('#accelerationZ > div > span');
  const RxDom = $('#gyroscopeX > div > span');
  const RyDom = $('#gyroscopeY > div > span');
  const RzDom = $('#gyroscopeZ > div > span');
  const OxDom = $('#orientationX > div > span');
  const OyDom = $('#orientationY > div > span');
  const OzDom = $('#orientationZ > div > span');
  const deviceMotionEventCallbackFunction = (deviceMotionEvent) => {
    let accelerationOnXAxis =
      deviceMotionEvent.accelerationIncludingGravity.x || 0;
    let accelerationOnYAxis =
      deviceMotionEvent.accelerationIncludingGravity.y || 0;
    let accelerationOnZAxis =
      deviceMotionEvent.accelerationIncludingGravity.z || 0;
    acceleration.x = Math.round(accelerationOnXAxis * accuracy) / accuracy;
    acceleration.y = Math.round(accelerationOnYAxis * accuracy) / accuracy;
    acceleration.z = Math.round(accelerationOnZAxis * accuracy) / accuracy;

    let gyroscopeOnXAxis = deviceMotionEvent.rotationRate.beta;
    let gyroscopeOnYAxis = deviceMotionEvent.rotationRate.gamma;
    let gyroscopeOnZAxis = deviceMotionEvent.rotationRate.alpha;
    gyroscope.x = Math.round(gyroscopeOnXAxis * accuracy) / accuracy;
    gyroscope.y = Math.round(gyroscopeOnYAxis * accuracy) / accuracy;
    gyroscope.z = Math.round(gyroscopeOnZAxis * accuracy) / accuracy;
  };
  const deviceOrientationEventCallbackFunction = (deviceOrientationEvent) => {
    let arrowObj = $('#arrow');

    if (deviceOrientationEvent.webkitCompassHeading) {
      // oc: orientation compass
      orientation.oc =
        Math.ceil(deviceOrientationEvent.webkitCompassHeading) || 0;
    } else {
      orientation.oc =
        Math.round((deviceOrientationEvent.alpha || 0) * accuracy) / accuracy;
    }

    orientation.x =
      Math.round((deviceOrientationEvent.alpha || 0) * accuracy) / accuracy;
    orientation.y =
      Math.round((deviceOrientationEvent.beta || 0) * accuracy) / accuracy;
    orientation.z =
      Math.round((deviceOrientationEvent.gamma || 0) * accuracy) / accuracy;
    // FIXME: The compass does not point to the right direction on the Android devices.
    arrowObj.css('transform', `rotate(${360 - orientation.oc}deg)`);
  };

  function addEventCallbackFunction() {
    [{'event': 'DeviceMotionEvent',
      'eventName': 'devicemotion',
      'eventHandler': deviceMotionEventCallbackFunction,
     },
     {'event': 'DeviceOrientationEvent',
      'eventName': 'deviceorientation',
      'eventHandler': deviceOrientationEventCallbackFunction,
    }].forEach(
      (obj) => {
        let deviceEvent = window[obj.event];

        // See: https://tinyurl.com/y3phm82o
        if ((typeof deviceEvent.requestPermission) === 'function') {
          /*
           * Call the permission requesting API to ask the permission.
           */
          deviceEvent.requestPermission()
            .then((response) => {
              if (response == 'granted') {
                window.addEventListener(obj.eventName, obj.eventHandler);
              }
            })
            .catch((error) => {
              console.error(error);
            });
        } else {
          window.addEventListener(obj.eventName, obj.eventHandler);
        }
      }
    );
  }

  function addCleanupFunction(deviceName) {
    document.onvisibilitychange = () => {
      if (document.visibilityState == 'hidden') {
        /*******************************************************************
        * According to this article: https://tinyurl.com/yc6h5z5k          *
        * The unload, the beforeunload and the pagehide events will not    *
        * be fired on the mobile devices. Also, that article also suggests *
        * that treat the hidden state as the last state on                 *
        * the mobile devices.                                              *
        * The hidden state is related to the visibilitychange event, For   *
        * more detail, please check https://tinyurl.com/yy2gjbad           *
        * To deal with this situation, I add an event handler for the      *
        * visibilitychange event to issue the deregister request and       *
        * re-register.                                                     *
        ********************************************************************/
        deregister();
      } else if (document.visibilityState == 'visible') {
        register(deviceName);
      }
    }

    if (browserInfo.browser.name == 'Safari') {
      // See: https://tinyurl.com/y5d7dv8r
      window.onpagehide = (pagehideEvent) => {
        deregister();
      };
    }
  }

  function onData(odf_name, data) {
    if (odf_name !== 'Vibration-O') {
      console.warn(`Unsupported odf: ${odf_name}`);
      return;
    }

    console.log(data[0]);
    if (data[0] > 0) {
      navigator.vibrate(data[0] * 100);
    }
  }

  function onRegister(result) {
    console.info('register:', result);
    $('#pageTitle').text(result ? result.d_name : 'Registration failed');
    const deviceName = result.d_name;

    if (result) {
      requestAnimationFrame(renderSensorValue);
      setInterval(pushDataToIoTtalk, interval);
      addCleanupFunction(deviceName);
    }
  }

  function onSignal(cmd, param) {
    console.debug('[cmd]', cmd, param);
    return true;
  }

  function renderSensorValue() {
    AxDom.text(acceleration.x);
    AyDom.text(acceleration.y);
    AzDom.text(acceleration.z);

    RxDom.text(gyroscope.x);
    RyDom.text(gyroscope.y);
    RzDom.text(gyroscope.z);

    OxDom.text(orientation.x);
    OyDom.text(orientation.y);
    OzDom.text(orientation.z);

    requestAnimationFrame(renderSensorValue);
  }

  function pushDataToIoTtalk() {
    dan2.push('Acceleration-I',
              [acceleration.x, acceleration.y, acceleration.z, ]);
    dan2.push('Gyroscope-I',
              [gyroscope.x, gyroscope.y, gyroscope.z, ]);
    dan2.push('Orientation-I',
              [orientation.x, orientation.y, orientation.z, ]);
  }

  function deregister() {
    if (!dan2.connected()) {
      return;
    }

    dan2.deregister();
  }

  function register(deviceName) {
    if (dan2.connected()) {
      return;
    }

    $.get('/ec_endpoint')
      .done((data) => {
        let ecEndpoint = data.ec_endpoint;
        window.dan2.register(
          ecEndpoint, {
            'id': id,
            'name': deviceName,
            'on_signal': onSignal,
            'on_data': onData,
            'idf_list': [
              ['Acceleration-I', ['g', 'g', 'g'], ],
              ['Gyroscope-I', ['g', 'g', 'g'], ],
              ['Orientation-I', ['g', 'g', 'g'], ],
            ],
            'odf_list': [
              ['Vibration-O', ['g', ], ],
            ],
            'profile': {
              'model': 'Smartphone',
            },
            'accept_protos': ['mqtt', ],
          },
          onRegister);
      })
      .fail((reason) => {
        $('#pageTitle').text('Registration failed.');
        console.error('Can not get the MQTT server information');
      });
  }

  function promptInputbox() {
    let deviceName = '';

    do {
      deviceName = window.prompt('Please enter the device name',
                                 `${Math.floor(Math.random() * 100)}.SmartPhone`);
    } while ( !deviceName );

    return deviceName;
  }

  if (!window.DeviceMotionEvent || !window.DeviceOrientationEvent) {
    alert('Your device does not support getting acceleration info from the browser');
    $('#pageTitle').text('Browser not supported')
  } else {
    const deviceName = promptInputbox();

    if (browserInfo.os.name == 'iOS') {
      /*
       * On the iOS-based devices, we need to get the permission grant
       * to access the acceleration, gryoscope information.
       * Also, this permission asking must be triggered by some specific events.
       * These events is listed on this webiste: https://tinyurl.com/y5mrw7pz
       */
      $('#permissionAskingBox').modal('show');
      $('#denyPermission').click(() => {
        $('#pageTitle').text('Permission denied');
      });
      $('#grantPermission').click(() => {
        addEventCallbackFunction();
        register(deviceName);
      });
    } else {
      addEventCallbackFunction();
      register(deviceName);
    }
  }
})();
