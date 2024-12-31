(() => {
  const browserInfo = bowser.parse(window.navigator.userAgent);
  const deviceName = `${Math.floor(Math.random() * 1000)}.Bulb`;
  const deviceModel = 'Bulb';
  const idfList = [];
  const id = uuidv4();
  const odfList = [['Color-O', ['r', 'g', 'b', ], ], ['Luminance-O', ['lax', ], ], ];
  let current_red_value = 255;
  let current_green_value = 255;
  let current_blue_value = 0;
  let current_luminance = 100;

  function draw(red_value, green_value, blue_value, luminance) {
    let bulb_red_value = Math.floor((red_value * luminance) / 100.0);
    let bulb_green_value = Math.floor((green_value * luminance) / 100.0);
    let bulb_blue_value = Math.floor((blue_value * luminance) / 100.0);
    $('.bulb-top, .bulb-middle-1, .bulb-middle-2, .bulb-middle-3, .bulb-bottom, .night').css(
      'background-color', `rgb(${bulb_red_value}, ${bulb_green_value}, ${bulb_blue_value})`
    );
  }

  function onRegister(result) {
    console.info('register:', result);
    $('#pageTitle').text(result ? result.d_name : 'Registration failed');

    if (result) {
      draw(current_red_value, current_green_value, current_blue_value,
           current_luminance);
    }
  }

  function onData(odf_name, data) {
    console.log(`${odf_name}: ${data}`);
    if (odfList.find(odfObject => odfObject[0] === odf_name) === undefined) {
      console.warn(`Unsupported odf: ${odf_name}`);
      return;
    }

    if (odf_name == 'Color-O') {
      current_red_value = data[0];
      current_green_value = data[1];
      current_blue_value = data[2];
    }
    else if (odf_name == 'Luminance-O'){
      current_luminance = data[0];
    }
    draw(current_red_value, current_green_value, current_blue_value,
         current_luminance);
  }

  function onSignal(cmd, param) {
    console.debug('[cmd]', cmd, param);
    return true;
  }

  function deregister() {
    if (!dan2.connected()) {
      return;
    }

    dan2.deregister();
  }

  function register(id, deviceModel, idfList, odfList, deviceName) {
    if (dan2.connected()) {
      return;
    }

    $.get('/iottalk/ccm/ec_endpoint')
      .done((data) => {
        let ecEndpoint = data.ec_endpoint;
        dan2.register(
          ecEndpoint, {
            'id': id,
            'name': deviceName,
            'on_signal': onSignal,
            'on_data': onData,
            'odf_list': odfList,
            'profile': {
              'model': deviceModel,
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

  register(id, deviceModel, idfList, odfList, deviceName);
})();
