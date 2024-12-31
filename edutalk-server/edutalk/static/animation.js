/* global daName:false idfs:false idfList:false fileList:false dmName:false dev:false title:false
   XLSX:false ajaxJson:false videoURL:false
*/

Vue.options.delimiters = ['[[', ']]'];
const animationApp = new Vue({
  el: '#animation-content',
  data: {
    videoURL,
    dataSource: '',
    startTime: new Date().toISOString(),
    endTime: new Date().toISOString(),
    intervalID: 0,
    pushInterval: 5,
    sensorInfo: {
      EduAcc_I: null,
      EduGyr_I: null,
      EduOri_I: null,
      EduMag_I: null,
      EduHum_I: 'morsensor',
      EduUV_I: 'morsensor',
      EduAlc_I: 'morsensor',
    },
    idfData: {},
    playlist: {},
    pause: true,
    percent: 0,
    speed: 1,
    workbook: {
      name: 'Database',
      data: {},
      list: fileList,
    },
    worksheet: '',
    mouseTime: '00:00.00',
  },
  computed: {
    idfListRC() {
      return idfList.filter((idf) => !this.m2Idfs.has(idf[0].name));
    },
    idfListM2() {
      return idfList.filter((idf) => this.m2Idfs.has(idf[0].name));
    },
    m2Idfs() {
      return new Set(ivList.flatMap((iv) => iv.params.filter((param) => param.device === 'M2')
        .map((param) => `M2${param.sensor}_I`)));
    },
    getStartTime: {
      get() {
        if (this.startTime.slice(-1) === 'Z') {
          const time = new Date(this.startTime);
          time.setTime(time.getTime() + (7 * 60 * 60 * 1000));
          return time.toISOString().split('.')[0];
        }
        return this.startTime;
      },
      set(value) {
        const time = new Date(value);
        time.setTime(time.getTime() + (8 * 60 * 60 * 1000));
        [this.startTime] = time.toISOString().split('.');
      },
    },
    getEndTime: {
      /**
       * endTime = '2022-04-06T17:47:34.919Z'
       * new Date('2022-04-06T17:47:34.919Z').getTime()
       * 1649267254919
       * getEndTime = '2022-04-07T01:47:34'
       * new Date('2022-04-07T01:47:34+08:00').getTime()
       * 1649267254000
       */
      get() {
        if (this.endTime.slice(-1) === 'Z') {
          const time = new Date(this.endTime);
          time.setTime(time.getTime() + (8 * 60 * 60 * 1000));
          return time.toISOString().split('.')[0];
        }
        return this.endTime;
      },
      set(value) {
        const time = new Date(value);
        time.setTime(time.getTime() + (8 * 60 * 60 * 1000));
        [this.endTime] = time.toISOString().split('.');
      },
    },
    progressBarStyle() {
      return { transform: `scaleX(${this.percent})` };
    },
    controlPanelStyle() {
      if (this.isPlayable()) {
        return {
          '--cursor': 'pointer',
          '--display': 'block',
          '--filter': 'invert(0)',
        };
      }
      return {
        '--cursor': 'default',
        '--display': 'none',
        '--filter': 'invert(0.6)',
      };
    },
    elapsedTime() {
      let time = this.percent * this.totalTime;
      if (Number.isNaN(time)) time = 0;
      return this.timeFormat(time);
    },
    hasSmartphone() {
      return ivList.find(
        ({ params }) => params.find(
          (param) => ['Smartphone', 'Range Slider', 'Input Box', 'Morsensor'].includes(param.device),
        ),
      ) !== undefined;
    },
    // data between start time and end time in each worksheet
    previewData() {
      const ret = {};

      if (Object.keys(this.workbook.data).length > 0) {
        Object.keys(this.workbook.data).forEach((sheetName) => {
          const sheetData = this.workbook.data[sheetName];
          ret[sheetName] = [sheetData[0]]; // [header] or [undefined] => length is 1
          if (sheetData[0] === undefined) return;
          if (sheetData[0].indexOf('TimeStamp') !== -1) {
            sheetData.slice(1).forEach((row) => {
              const time = row[0];
              if (new Date(animationApp.getStartTime) <= new Date(time)
                && new Date(time) <= new Date(animationApp.getEndTime)) {
                ret[sheetName].push(row);
              }
            });
          } else {
            ret[sheetName] = sheetData;
          }
        });
      }

      return ret;
    },
    inputSpeed: {
      get() {
        return this.speed;
      },
      set(value) {
        if (Number.isNaN(Number(value)) || Number(value) <= 0) return;

        /**
         * Replay DA will skip some data if some timestamps have the same value
         * when divided by the interval value and upward to the nearest integer.
         */
        const interval = this.pushInterval * value;
        const reject = Object.values(this.playlist).some((times) => {
          const obj = times.reduce((c, t) => {
            const key = Math.ceil(t / interval);
            c[key] = (c[key] || 0) + 1;
            return c;
          }, {});
          return Object.values(obj).some((counter) => counter > 1);
        });
        if (reject) return;

        this.speed = value;
      },
    },
    idfNames() {
      return idfs.map((x) => x[0].replace('-I', '_I'));
    },
  },
  // self-defined function for this vue object
  methods: {
    chooseDataSource(event) {
      if (event) {
        this.dataSource = event.target.text;
        if (this.dataSource === 'Live Data') {
          sessionStorage.clear();
          if (this.hasSmartphone) this.showQRcode();
          this.bindM2();
        }
        if (this.dataSource === 'Historical Data') {
          this.openForm();
          if (this.replayDA) {
            ajaxJson(
              urls.rcBind(this.replayDA.dan.ctx.appID),
              'POST',
              {},
              () => {
                console.log('input device bind success');
              },
              () => {
                console.error('input device bind failed');
              },
            ).always(() => this.bindM2(true));
          } else {
            this.bindM2(true);
          }

          if (Object.keys(this.workbook.data).length === 0) this.queryDataFromServer();
        }

        const action = (this.dataSource === 'Live Data') ? 'bind' : 'unbind';
        ajaxJson(
          urls.lecture[action],
          'POST',
          {},
          () => console.log(`simple logger ${action} success`),
          () => console.error(`simple logger ${action} failed`),
        );
      }
    },
    showQRcode() {
      $('#QRcode_modal').modal('show');
    },
    openForm() {
      $('#choose-date-panel').modal('show');
      this.callPause();
    },
    closeForm() {
      $('#choose-date-panel').modal('hide');
    },
    timeFormat(time) {
      const min = parseInt(time / 60, 10);
      const sec = (time % 60).toFixed(2);
      return `${String(min).padStart(2, '0')}:${String(sec).padStart(5, '0')}`;
    },
    /* ==  Handle File start == */
    chooseHistoricalDataSource(event) {
      if (event) {
        if (event.target.text === 'Add New Data') {
          event.preventDefault();
          $('#upload:hidden').trigger('click');
          return;
        }
        this.workbook.name = event.target.text;
        this.queryDataFromServer();
      }
    },
    onFileChange(event) {
      const { files } = event.target;
      if (files && files[0]) {
        const f = files[0];
        const reader = new FileReader();
        const rABS = !!reader.readAsBinaryString;
        reader.onload = (e) => {
          let data = e.target.result;
          let wb;
          let arr;
          const readtype = { type: rABS ? 'binary' : 'base64' };
          if (!rABS) {
            arr = this.fixdata(data);
            data = btoa(arr);
          }
          try {
            wb = XLSX.read(data, readtype);
            const result = {};
            let first = true;
            const skip = [];
            wb.SheetNames.forEach((sheetName) => {
              if (!this.idfNames.includes(sheetName)) {
                skip.push(sheetName);
                return;
              }
              if (first) {
                this.worksheet = sheetName;
                first = false;
              }
              const roa = XLSX.utils.sheet_to_json(wb.Sheets[sheetName], { raw: false });
              if (roa.length > 0) result[sheetName] = roa;
            });
            if (skip.length > 0) {
              alert(`This lecture doesn't use the following IDF(s): ${skip}.\
                    \nWe'll skip these feature(s).\
                    \nYou can upload again using the same filename to cover the old data.`);
            }
            Object.keys(result).forEach((sheetName) => {
              const sheetData = result[sheetName];
              const newFormatData = [Object.keys(sheetData[0])];
              sheetData.forEach((d) => newFormatData.push(Object.values(d)));
              result[sheetName] = newFormatData;
            });
            this.workbook.data = result;
            ajaxJson(
              urls.lecture.upload_historical_data,
              'POST',
              {
                filename: f.name,
                data: this.workbook.data,
              },
              (res) => {
                this.workbook.list = res.file_list;
                this.workbook.name = f.name;
                this.showGrid();
              },
            );
          } catch (err) { console.log(err); }
        };
        if (rABS) reader.readAsBinaryString(f);
        else reader.readAsArrayBuffer(f);
      }
    },
    fixdata(data) {
      let o = '';
      const w = 10240;
      for (let l = 0; l < data.byteLength / w; l += 1) {
        o += String.fromCharCode.apply(null, new Uint8Array(data.slice(l * w, l * w + w)));
      }
      o += String.fromCharCode.apply(null, new Uint8Array(data.slice(o.length)));
      return o;
    },
    changeWorksheet(event) {
      this.worksheet = event.target.text;
      this.showGrid();
    },
    cleanWroksheet() {
      $('div#worksheet-table').empty();
      this.worksheet = '';
      this.workbook.data = {};
    },
    onTimeChange() {
      if (this.workbook.name === 'Database') this.queryDataFromServer();
      else this.showGrid();
    },
    showGrid() {
      if (Object.keys(this.previewData).length === 0) return;
      $('div#worksheet-table').empty();
      $('div#worksheet-table').Grid({
        columns: ['TimeStamp'],
        data: [{ TimeStamp: '1970-01-01T00:00:00.000000Z' }],
      }).updateConfig({
        pagination: { limit: 10 },
        columns: this.previewData[this.worksheet][0],
        data: this.previewData[this.worksheet].slice(1),
        style: {
          container: {
            'font-size': '13px',
          },
          th: {
            'background-color': 'rgba(0, 0, 0, 0.1)',
            color: '#000',
            'text-align': 'center',
            padding: '10px 0px',
            width: '25%',
          },
          td: {
            'text-align': 'center',
            padding: 0,
            width: '25%',
          },
        },
      }).forceRender();
    },
    queryDataFromServer() {
      this.cleanWroksheet();
      $('#loading-spinner').show();

      const source = this.workbook.name;
      const option = {};
      if (source === 'Database') {
        option.idf_names = this.idfNames;
        option.start_time = new Date(`${this.getStartTime}+08:00`).getTime();
        option.end_time = new Date(`${this.getEndTime}+08:00`).getTime();
      } else {
        option.filename = source;
      }

      ajaxJson(
        urls.lecture.query_historical_data,
        'POST',
        option,
        (res) => {
          $('#loading-spinner').hide();
          this.workbook.data = res.data;
          [this.worksheet] = Object.keys(this.workbook.data);
          this.showGrid();
        },
      );
    },
    downloadWorkbook() {
      const wb = XLSX.utils.book_new();
      Object.keys(this.workbook.data).forEach((sheetName) => {
        // walks an "array of arrays" in row-major order, generating a worksheet object
        const ws = XLSX.utils.aoa_to_sheet(this.previewData[sheetName]);
        // add worksheet to workbook
        XLSX.utils.book_append_sheet(wb, ws, sheetName);
      });

      // write workbook
      XLSX.writeFile(wb, `${this.workbook.name}_from${this.getStartTime}to${this.getEndTime}.xlsx`);
    },
    /* ==  Handle File end == */
    /* ==  replay DA start == */
    confirmData() {
      sessionStorage.clear();
      this.callStop();

      this.playlist = {};
      const firstTime = this.computeTimes();
      Object.keys(this.previewData).forEach((sheetName) => {
        const originalData = this.previewData[sheetName];
        if (originalData[0] === undefined) return;

        const sheetData = {};
        const hasTimeStamp = originalData[0].indexOf('TimeStamp') !== -1;
        const interval = Math.floor((this.totalTime * 1000) / (originalData.length - 2));
        let preData = null;
        originalData.slice(1).forEach((d, index) => {
          const currData = hasTimeStamp ? d.slice(1) : d;
          if (JSON.stringify(preData) !== JSON.stringify(currData)) {
            const time = hasTimeStamp ? (new Date(d[0]) - firstTime) : (index * interval);
            sheetData[time] = currData;
            preData = currData;
          }
        });
        sessionStorage.setItem(sheetName, JSON.stringify(sheetData));
        this.playlist[sheetName] = Object.keys(sheetData)
          .sort((a, b) => parseInt(a, 10) - parseInt(b, 10))
          .reverse();
      });
      this.workbook.data = {};

      this.closeForm();
    },
    computeTimes() {
      let firstTime = Number.POSITIVE_INFINITY;
      let lastTime = Number.NEGATIVE_INFINITY;
      Object.keys(this.previewData).forEach((sheetName) => {
        const originalData = this.previewData[sheetName];
        if (originalData[0] === undefined) return;

        if (originalData[0].indexOf('TimeStamp') === -1) return;

        const sheetData = originalData.slice(1);
        if (sheetData[0] === undefined) return;

        if (new Date(sheetData[0][0]) < firstTime) {
          firstTime = new Date(sheetData[0][0]);
        }
        if (new Date(sheetData.slice(-1)[0][0]) > lastTime) {
          lastTime = new Date(sheetData.slice(-1)[0][0]);
        }
      });

      if (lastTime > firstTime) this.totalTime = (lastTime - firstTime) / 1000;
      else {
        // all data has no timestamp; set the data interval to 0.2s
        const lengthArray = Object.values(this.previewData).map((x) => x.length - 2);
        this.totalTime = Math.max(...lengthArray) * 0.2;
      }

      return firstTime;
    },
    isPlayable() {
      return Object.keys(this.playlist).length > 0;
    },
    callPlay(init = true) {
      if (!this.isPlayable()) return;
      this.pause = false;
      if (Number(this.speed) !== this.speed) this.speed = 1;
      if (init) this.initPush();
      if (this.intervalID === 0) this.startTimer();
    },
    callPause() {
      if (!this.isPlayable()) return;
      this.pause = true;
    },
    callStop() {
      if (!this.isPlayable()) return;
      clearInterval(this.intervalID);
      this.intervalID = 0;
      this.percent = 0;
      this.pause = true;
    },
    getPercentFromEvent(event) {
      const left = event.pageX - event.target.getBoundingClientRect().left;
      const width = event.target.clientWidth;
      if (left / width < 0) return 0;
      if (left / width > 1) return 1;
      return left / width;
    },
    getMouseTime(event) {
      if (!this.isPlayable()) return;
      const time = this.getPercentFromEvent(event) * this.totalTime;
      this.mouseTime = this.timeFormat(time);

      const label = $('.percentage-bar .mouse-display');
      label.css('left', event.pageX - event.target.getBoundingClientRect().left - label.width() / 2);
    },
    updatePercentByUser(event) {
      if (!this.isPlayable()) return;
      this.callPause();
      // start by click progress bar
      if (this.intervalID === 0) {
        this.initPush();
      }
      // restore last state
      this.percent = this.getPercentFromEvent(event);
      const interval = this.pushInterval * this.speed;
      const nowTime = this.percent * this.totalTime * 1000;
      const lastTime = nowTime - interval;
      Object.keys(this.playlist).forEach((idf) => {
        const t = this.playlist[idf].find((time) => lastTime >= time);
        if (t) {
          let data = JSON.parse(sessionStorage.getItem(idf))[t];
          data = data.map((d) => (Number.isNaN(Number(d)) ? d : Number(d)));
          this.push(idf, data);
        }
      });
      this.callPlay(false);
    },
    push(idfName, data) {
      if (!(data instanceof Array)) data = [data];
      data.push(0); // dummy datetime
      if (this.sensorInfo[idfName] === undefined) data.push(idfName);
      this.idfData[idfName] = data;
    },
    initPush() {
      idfs.forEach((idf) => {
        const value = parseFloat(idf[1]);
        if (this.sensorInfo[idf[0]] === null) {
          this.push(idf[0], [0, 0, 0]); // smartphone
          return;
        }
        this.push(idf[0], [value]);
      });
    },
    startTimer() {
      if (this.intervalID != null) clearInterval(this.intervalID);

      this.intervalID = setInterval(() => {
        if (this.pause) return;

        const interval = this.pushInterval * this.speed;
        const nowTime = this.percent * this.totalTime * 1000;
        const lastTime = nowTime - interval;

        Object.keys(this.playlist).forEach((idf) => {
          const t = this.playlist[idf].find((time) => lastTime < time && time <= nowTime);
          if (t) {
            let data = JSON.parse(sessionStorage.getItem(idf))[t];
            data = data.map((d) => (Number.isNaN(Number(d)) ? d : Number(d)));
            this.push(idf, data);
          }
        });

        if (Math.floor(this.percent) === 1) {
          this.callStop();
          return;
        }
        this.percent += (interval / (1000 * this.totalTime));
      }, this.pushInterval);
    },
    /* ==  replay DA end == */
    bindM2(replay = false) {
      if (replay && this.replayM2) {
        ajaxJson(
          urls.m2Bind(this.replayM2.dan.ctx.appID),
          'POST',
          {},
          () => console.log('replay m2 device bind success'),
          () => console.error('replay m2 device bind failed'),
        );
      } else {
        ajaxJson(
          urls.m2Bind(),
          'POST',
          {},
          () => console.log('m2 device bind success'),
          () => console.error('m2 device bind failed'),
        );
      }
    },
  },
  // Ref: https://v2.vuejs.org/v2/api/#mounted
  mounted() {
    this.$nextTick(() => {
      // Code that will run only after the entire view has been rendered
      sessionStorage.clear();

      idfList.forEach((idf) => {
        idf[0] = new Function(
          `return function ${idf[0].replace('-I', '_I')}() {\
            let data = animationApp.idfData[arguments.callee.name];\
            if (data) {\
              delete animationApp.idfData[arguments.callee.name];\
              return data;\
            }\
          }`,
        )();
      });

      if (this.idfListRC.length > 0) {
        this.replayDA = new iottalkjs.DAI({
          apiUrl: urls.csmUrl,
          deviceModel: dmName,
          deviceName: dev,
          idfList: this.idfListRC,
          odfList: [],
          pushInterval: this.pushInterval / 1000,
          onConnect: () => {
            document.title = title;
          },
        });
        this.replayDA.run();
      }

      if (this.idfListM2.length > 0) {
        this.replayM2 = new iottalkjs.DAI({
          apiUrl: urls.csmUrl,
          deviceModel: 'M2',
          deviceName: `M2${dev}`,
          idfList: this.idfListM2,
          odfList: [],
          pushInterval: this.pushInterval / 1000,
          onConnect: () => {
            document.title = title;
          },
        });
        this.replayM2.run();
      }
    });
  },
});

window.onbeforeunload = function () {
  ajaxJson(
    urls.m2UnBind(),
    'POST',
    {},
    () => console.log('m2 device unbind success'),
    () => console.error('m2 device unbind failed'),
  );
  ajaxJson(
    urls.vpUnBind(),
    'POST',
    {},
    () => console.log('vp unbind success'),
    () => console.error('vp unbind failed'),
  );
};
