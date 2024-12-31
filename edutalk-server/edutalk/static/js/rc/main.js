/* global idfs:false idfList:false Magnetometer:false dmName:false dev:false
excludeIdfs:true bind_callbacks:true exclude_idfs:false da:false */

Vue.options.delimiters = ['[[', ']]'];
const RCapp = new Vue({
  el: '#RC',
  data: {
    pushInterval: 0,
    collectDataInterval: 5,
    ivList,
    sensorInfo: {
      EduAcc_I: ['acc', null],
      EduGyr_I: ['gyr', null],
      EduOri_I: ['ori', null],
      EduMag_I: ['mag', null],
      EduHum_I: ['hum', 'morsensor'],
      EduUV_I: ['uv', 'morsensor'],
      EduAlc_I: ['alc', 'morsensor'],
    },
    idfs,
    idfData: {},
    sensorData: {
      acc: {},
      gyr: {},
      ori: {},
      mag: {},
      hum: {},
      uv: {},
      alc: {},
    },
    permissionPromises: [],
  },
  computed: {
    sensorList() {
      const ret = {};
      this.ivList.forEach((iv) => iv.params.reduce((c, { device, sensor }) => {
        if (sensor && device === 'Smartphone') [c[sensor]] = this.sensorInfo[`Edu${sensor.slice(0, 3)}_I`];
        return c;
      }, ret));
      return ret;
    },
    idfNames() {
      return this.idfs.map((x) => x[0].replace('-I', '_I'));
    },
    rcIdfs() {
      return idfs.filter((x) => !this.excludeIdfs.has(x[0]));
    },
    excludeIdfs() {
      return new Set(exclude_idfs);
    },
  },
  methods: {
    getIdfName(ivIndex, paramIndex) {
      let idfIndex = paramIndex;
      for (let i = 0; i < ivIndex; i += 1) {
        idfIndex += this.ivList[i].params.length;
      }
      return this.idfNames[idfIndex];
    },
    push(idfName, data) {
      if (!(data instanceof Array)) data = [data];
      this.idfData[idfName.replace('-I', '_I')] = data;
    },
    initPush() {
      this.idfs.forEach((idf) => {
        const dateTime = new Date().getTime();
        if (this.sensorInfo[idf[0]] === undefined) {
          this.push(idf[0], [idf[1], dateTime, idf[0]]);
          return;
        }
        if (this.sensorInfo[idf[0]][1] === null) {
          this.push(idf[0], [0, 0, 0, dateTime]); // smartphone
          return;
        }
        this.push(idf[0], [idf[1], dateTime]);
      });
    },
    sliderHandler() {
      $('input[type="range"]').rangeslider({
        // Feature detection the default is `true`.
        // Set this to `false` if you want to use
        // the polyfill also in Browsers which support
        // the native <input type="range"> element.
        polyfill: false,

        // Default CSS classes
        rangeClass: 'rangeslider',
        disabledClass: 'rangeslider--disabled',
        horizontalClass: 'rangeslider--horizontal',
        verticalClass: 'rangeslider--vertical',
        fillClass: 'rangeslider__fill',
        handleClass: 'rangeslider__handle',

        // Callback function
        onInit() {
          this.output = $('<output class="column has-text-centered">').insertAfter(this.$range).html(this.$element.val());
        },
        // Callback function
        onSlide(position, value) {
          // console.log('onSlide:',position,value);
          this.output.html(value);
        },
        // Callback function
        onSlideEnd(position, value) {
          const idf = this.$element.attr('name');
          const dateTime = new Date().getTime();
          console.log(`onSlideEnd: ${this.identifier}, ${idf}: ${value}`);
          RCapp.push(idf, [parseFloat(value), dateTime, idf]);
        },
      });
    },
    inputNumHandler() {
      $('.submit-btn').on('click', function () {
        $(this).siblings('.error-msg').hide();
        const idf = $(this).parent().attr('name');
        const currentValue = $(this).siblings('.input-num').val();
        console.log(`${idf}: ${currentValue}`);
        if (currentValue) {
          const dateTime = new Date().getTime();
          RCapp.push(idf, [currentValue, dateTime, idf]);
        } else {
          $(this).siblings('.error-msg').show();
        }
      });
    },
    pushSensorValue() {
      Object.keys(this.sensorInfo).forEach((sensorName) => {
        const tag = this.sensorInfo[sensorName][0];
        const type = this.sensorInfo[sensorName][1];
        const dateTime = new Date().getTime();
        if (!RCapp.idfNames.includes(sensorName) || $(`#${tag}_btn`).text() === 'off') {
          return;
        }
        const Sx = RCapp.sensorData[tag].x || null;
        const Sy = RCapp.sensorData[tag].y || null;
        const Sz = RCapp.sensorData[tag].z || null;

        if (type === 'morsensor') {
          RCapp.push(sensorName, [Number(Sx.toFixed(5)), dateTime]);
          return;
        }
        if (Sx && Sy && Sz) {
          RCapp.push(
            sensorName,
            [Number(Sx.toFixed(5)), Number(Sy.toFixed(5)), Number(Sz.toFixed(5)), dateTime],
          );
        }
      });

      // todo: move push to event handler and separate push for different sensor
      // sample rate on browser is limited to 60 HZ !
      setTimeout(this.pushSensorValue, 1000 / 60);
    },
    setSmartphoneSensorHandler() {
      [
        {
          Event: DeviceMotionEvent,
          eventListener: 'devicemotion',
          sensorTag: 'acc',
          controlBtnSelector: '#acc_btn',
        },
        {
          Event: DeviceMotionEvent,
          eventListener: 'devicemotion',
          sensorTag: 'gyr',
          controlBtnSelector: '#gyr_btn',
        },
        {
          Event: DeviceOrientationEvent,
          eventListener: 'deviceorientation',
          sensorTag: 'ori',
          controlBtnSelector: '#ori_btn',
        },
      ].forEach((e) => {
        this.permissionPromises.push(
          new Promise((resolve, reject) => {
            if (typeof e.Event.requestPermission === 'function') {
              e.Event.requestPermission()
                .then((permissionState) => {
                  if (permissionState === 'granted') {
                    window.addEventListener(e.eventListener, (event) => {
                      eventHandler(event, e.sensorTag);
                    });
                    RCapp.turnOnBtnObj($(e.controlBtnSelector));
                    resolve();
                  }
                  reject();
                })
                .catch(console.error);
            } else {
              window.addEventListener(e.eventListener, (event) => eventHandler(event, e.sensorTag));
              RCapp.turnOnBtnObj($(e.controlBtnSelector));
              resolve();
            }
          }),
        );
      });

      if ('Magnetometer' in window) {
        const sensor = new Magnetometer({ frequency: 50 });// 50hz, rate=20ms
        sensor.addEventListener('reading', (event) => eventHandler(event, 'mag'));
        sensor.start();
        RCapp.turnOnBtnObj($('#mag_btn'));
      }

      function eventHandler(event, tag) {
        if (!Object.values(RCapp.sensorList).includes(tag)) {
          return;
        }
        const smartphoneInfo = {
          acc: 'accelerationIncludingGravity',
          gyr: 'rotationRate',
          mag: 'target',
        };
        const tmp = event[smartphoneInfo[tag]];
        if (tag === 'acc') {
          RCapp.sensorData.acc.x = tmp.x;
          RCapp.sensorData.acc.y = tmp.y;
          RCapp.sensorData.acc.z = tmp.z;
        } else if (tag === 'gyr') {
          RCapp.sensorData.gyr.x = tmp.alpha;
          RCapp.sensorData.gyr.y = tmp.beta;
          RCapp.sensorData.gyr.z = tmp.gamma;
        } else if (tag === 'ori') {
          RCapp.sensorData.ori.x = event.alpha;
          RCapp.sensorData.ori.y = event.beta;
          RCapp.sensorData.ori.z = event.gamma;
        } else if (tag === 'mag') {
          RCapp.sensorData.mag.x = tmp.x;
          RCapp.sensorData.mag.y = tmp.y;
          RCapp.sensorData.mag.z = tmp.z;
        }
        // todo: push at here and separate push for different sensor
        // RCapp.pushSensorValue();
      }

      this.sensorHandler();
    },
    setMorsensorHandler() {
      if (this.idfNames.includes('EduHum_I') || this.idfNames.includes('EduUV_I') || this.idfNames.includes('EduAlc_I')) {
        getMorsensorData();
      } else {
        $('.hint-message').remove();
      }

      function getMorsensorData() {
        $.ajax({
          url: 'http://localhost:8080/dataget',
          type: 'GET',
        }).done((data) => {
          RCapp.sensorData.hum.x = data.humi;
          RCapp.sensorData.uv.x = data.uv;
          RCapp.sensorData.alc.x = data.alc;

          if ($('.hint-message').is(':visible')) {
            $('.hint-message').hide();
            RCapp.turnOnBtnObj($('.morsensor_btn'));
          }
        }).fail(() => {
          $('.hint-message').show();
          RCapp.turnOffBtnObj($('.morsensor_btn'));
        });

        setTimeout(getMorsensorData, RCapp.collectDataInterval);
      }
    },
    sensorHandler() {
      Promise.all(this.permissionPromises).then(() => {
        requestAnimationFrame(RCapp.updateLayout);
        RCapp.pushSensorValue();
      });
    },
    updateLayout() {
      Object.keys(this.sensorInfo).forEach((sensorName) => {
        const tag = this.sensorInfo[sensorName][0];
        const type = this.sensorInfo[sensorName][1];
        if (!RCapp.idfNames.includes(sensorName)) {
          return;
        }

        const unixTimestamp = new Date(new Date().getTime());
        const commonTime = `${unixTimestamp.toLocaleTimeString()}.${unixTimestamp.getMilliseconds()}`;

        if (type === 'morsensor') {
          $(`#${tag}_x`).text(Number.parseFloat(RCapp.sensorData[tag].x).toFixed(2));
          $(`#${tag}_time`).text(commonTime);
        } else {
          $(`#${tag}_x`).text(Number.parseFloat(RCapp.sensorData[tag].x).toFixed(2));
          $(`#${tag}_y`).text(Number.parseFloat(RCapp.sensorData[tag].y).toFixed(2));
          $(`#${tag}_z`).text(Number.parseFloat(RCapp.sensorData[tag].z).toFixed(2));
          $(`#${tag}_time`).text(commonTime);
        }
      });

      requestAnimationFrame(this.updateLayout);
    },
    switchBtn(e) {
      const obj = $('.sensor-block').find(`#${e.target.id}`);
      if (obj.text() === 'off') {
        this.turnOnBtnObj(obj);
      } else {
        this.turnOffBtnObj(obj);
      }
    },
    turnOnBtnObj(obj) {
      obj.text('on');
      obj.removeClass('btn-danger').addClass('btn-success');
    },
    turnOffBtnObj(obj) {
      obj.text('off');
      obj.removeClass('btn-success').addClass('btn-danger');
    },
  },
  // Ref: https://v2.vuejs.org/v2/api/#mounted
  mounted() {
    this.$nextTick(function () {
       // 在這裡加入兩行檢查
       console.log('Received ivList:', this.ivList);
       console.log('Params devices:', this.ivList.map(iv => iv.params.map(p => p.device)));
      // Code that will run only after the entire view has been rendered
      $('#permission_modal').modal('show', { backdrop: 'static', keyboard: false });
      $('#permission_modal').bind('click', () => {
        if (!this.rcIdfs.every(([idf]) => RCapp.flags[idf.replace('_I', '-I')] === true)) return;
        RCapp.setSmartphoneSensorHandler();
        RCapp.setMorsensorHandler();
        setTimeout(() => {
          RCapp.initPush();
          $('#permission_modal').modal('hide');
        }, 1000);
      });
      this.inputNumHandler();
      this.sliderHandler();

      idfList.forEach((idf) => {
        idf[0] = new Function(
          `return function ${idf[0].replace('-I', '_I')}() {\
            let data = RCapp.idfData[arguments.callee.name];\
            if (data) {\
              delete RCapp.idfData[arguments.callee.name];\
              return data;\
            }\
          }`,
        )();
      });

      window.da = new iottalkjs.DAI({
        apiUrl: urls.csmUrl,
        deviceModel: dmName,
        deviceName: dev,
        idfList,
        odfList: [],
        pushInterval: this.pushInterval / 1000,
        onRegister,
      });
      da.run();
      this.flags = da.flags;

      function onRegister() {
        const url = urls.rcBind(this.appID);
        let chain = $.ajax({
          type: 'POST',
          headers: { 'x-csrf-token': csrf.token },
          url,
        });
        chain = chain.then(
          () => {
            console.log('device binding success');
            if (urls.bind_callbacks.length > 0) {
              return $.ajax({
                type: 'POST',
                headers: { 'x-csrf-token': csrf.token },
                url: urls.bind_callbacks[0],
              });
            }
            return Promise.reject();
          },
          () => {
            console.error('device binding failed');
          },
        );

        for (let i = 0; i < urls.bind_callbacks.length; i++) {
          chain = chain.then(
            () => {
              console.log(`${urls.bind_callbacks[i]} success`);
              if (i + 1 < urls.bind_callbacks.length) {
                return $.ajax({
                  type: 'POST',
                  headers: { 'x-csrf-token': csrf.token },
                  url: urls.bind_callbacks[i + 1],
                });
              }
              return Promise.reject();
            },
            () => {
              console.error(`${urls.bind_callbacks[i]} failed`);
            },
          );
        }
      }
    });
  },
});
