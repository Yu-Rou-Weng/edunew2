/* global daName:false unitList:false ajaxJson:false lectureName:false hackmdURL:false
   urlHistory:false  videoURL:false videoHistory:false animationApp:false
   sensorOptions:false output_variables:false actuatorDm:false available_sensors_device:false
   available_actuators_device:false
*/

Vue.options.delimiters = ['[[', ']]'];
const app = new Vue({
  el: '#card',
  data: {
    lectureId: null,
    newLectureName: '',
    lectureNameError: '',
    lectureName,
    hackmdURL,
    urlHistory,
    videoURL,
    videoHistory,
    odm: daName,
    unitList,
    sensorOptions,
    output_variables,
    selectedActuatorVar: 0,
    actuatorDm,
    /* ivList: [{
        giv_name: name of a global input variable,
        type: type of variable,
        index:   ''  , if no duplicate giv_name
              integer, otherwise
        params: [{
          'model': Smartphone or M2,
          'mac_addr': mac_addr of sensor model,
          'device': Range Slider or Input Box or Smartphone or Morsensor or M2,
          'sensor': sensor,           // optional, for Smartphone and Morsensor
          'sensor_unit': sensor unit, // default is 'None'
          'min': min,                 // default is 0
          'max': max,                 // default is 10
          'default': default value,   // default is 5
          'unit': df unit,            // default is 'None'
          'type': type,               // default is 'float'
          'function': join function   // optional, for multidimensional sensor
        }, ...]
      }, ...]

      settingIv: {                    // the iv in setting area
        show: boolean,                // whether show the setting area
        giv_name: iv.giv_name ,
        type: type of variable,
        params: iv.params
      }

      output_variables: [
        # only 'actuator' and 'odf' are updatable
        {
          'name': name of variable,
          'type': type of variable,
          'dim': number of dimensions,
          'default': actuator_var['default'],
          'idf': [df['df_name'], [''] * len(df['parameter'])],
          'actuator': '',  # dm of actuator
          'odf': '',  # odf of actuator
          'mac_addr': '',  # mac_addr of actuator
         }, ...
      ]
    */
    ivList,
    settingIv: {
      show: false,
      giv_name: '',
      type: '',
      index: '',
      params: [],
    },
    /* deviceAddresses: {
      Smartphone: '',
      M2: '',
    }, */
    deviceAddresses: Object.fromEntries(
      Object.entries(sensorOptions)
        .filter((([k]) => k !== 'Input Box' && k !== 'Range Slider' && k !== 'Morsensor'))
        .map(([k]) => [k, '']),
    ),
    err: {
      type: '',
      msg: '',
    },
  },
  computed: {
    idm() { return `${this.odm}RC`; },
    dfs() {
      /* odfs: [{
          'name': odf name,
          'unit': [
            param unit,  // y1,
            param unit,  // y2, optional
            param unit   // y3, optional
          ],
          'type': [
            param type,  // y1,
            param type,  // y2, optional
            param type   // y3, optional
          ],
        }, ...]

        idfs: [{
          'name': idf name,
          'type': type,             // optional
          'min': min,               // optional
          'max': max,               // optional
          'default': default value  // optional
        }, ...]

        joins: {
          odf_name: [
            [idf name, fn name, default value],  // y1,
            [idf name, fn name, default value],  // y2, optional
            [idf name, fn name, default value]   // y3, optional
          ], ...}
      */

      const odfs = [];
      const idfs = [];
      const joins = {};
      const smSensorList = [];

      let numIndex = 0;
      let rangeIndex = 0;

      this.ivList.forEach((iv) => {
        const front = this.odm + iv.giv_name.charAt(0).toUpperCase() + iv.giv_name.slice(1);
        const index = iv.index || '';
        const odf = {
          name: `${front}-O${index}`,
          unit: [],
          type: [],
        };

        this.$set(joins, odf.name, []);

        iv.params.forEach((param) => {
          const idf = {};
          switch (param.device) {
            case 'Input Box':
              idf.name = `${this.odm}Number-I${(numIndex += 1).toString()}`;
              idf.type = param.type;
              idf.default = param.default;
              break;
            case 'Range Slider':
              idf.name = `${this.odm}RangeSlider-I${(rangeIndex += 1).toString()}`;
              idf.type = param.type;
              idf.min = param.min;
              idf.max = param.max;
              idf.default = param.default;
              break;
            case 'Smartphone':
            case 'Morsensor':
              idf.name = `Edu${param.sensor.slice(0, 3)}-I`;
              break;
            default: // others like M2
              idf.name = `${param.device}${param.sensor}-I`;
          }

          odf.unit.push(param.unit);
          odf.type.push(param.type);

          joins[odf.name].push([idf.name, param.function, param.default]);

          // the count of sensor(except below) is at most 1
          if (smSensorList.includes(`${param.device}-${param.sensor}`)) return;
          if (param.device !== 'Range Slider' && param.device !== 'Input Box') smSensorList.push(`${param.device}-${param.sensor}`);

          idfs.push(idf);
        });

        odfs.push(odf);
      });

      return [odfs, idfs, joins];
    },
    odfs() { return this.dfs[0]; },
    idfs() { return this.dfs[1]; },
    joins() { return this.dfs[2]; },
    availableSensorDevices() {
      const availableDevices = [];

      for (const model of Object.keys(available_sensors_device)) {
        for (const device of available_sensors_device[model]) {
          device.model = model;
          availableDevices.push(device);
        }
      }

      return availableDevices;
    },
    availableActuators() {
      const availableActuators = new Set(['']);
      const { dim } = this.output_variables[this.selectedActuatorVar];
      for (const actuator of Object.keys(actuatorDm)) {
        for (const odf of Object.keys(actuatorDm[actuator].odfs)) {
          if (actuatorDm[actuator].odfs[odf].dim == dim) {
            availableActuators.add(actuator);
          }
        }
      }
      return [...availableActuators];
    },
    availableActuatorDevices() {
      const availableActuators = new Set();
      const { dim } = this.output_variables[this.selectedActuatorVar];
      for (const actuator of Object.keys(actuatorDm)) {
        for (const odf of Object.keys(actuatorDm[actuator].odfs)) {
          if (actuatorDm[actuator].odfs[odf].dim == dim) {
            availableActuators.add(actuator);
          }
        }
      }
      const availableDevices = [];
      for (const actuator of availableActuators) {
        for (const device of available_actuators_device[actuator]) {
          device.model = actuator;
          availableDevices.push(device);
        }
      }
      return availableDevices;
    },
    availableActuatorOdfs() {
      const availableOdfs = [''];
      const { dim } = this.output_variables[this.selectedActuatorVar];
      const { actuator } = this.output_variables[this.selectedActuatorVar];
      if (actuator) {
        for (const odf of Object.keys(actuatorDm[actuator].odfs)) {
          if (actuatorDm[actuator].odfs[odf].dim == dim) {
            availableOdfs.push(odf);
          }
        }
      }
      return availableOdfs;
    },
  },
  watch: {
    // keep all model with same device addr !!!
    deviceAddresses: {
      handler() {
        this.ivList.forEach((iv) => {
          for (const param of iv.params) {
            if (Object.keys(this.deviceAddresses).includes(param.model)) {
              param.mac_addr = this.deviceAddresses[param.model];
            }
          }
        });
      },
      deep: true,
      // immediate: true,
    },
  },
  // self-defined function for this vue object
  methods: {
    saveLectureName() {
      if (!this.newLectureName.trim()) {
        this.lectureNameError = '课程名称不能为空';
        return;
      }
      
      // 检查课程名称是否已存在
      ajaxJson(
        '/edutalk/lecture/check-name',
        'POST',
        { name: this.newLectureName },
        (response) => {
          if (response.exists) {
            this.lectureNameError = '课程名称已存在';
          } else {
            this.lectureName = this.newLectureName;
            $('#lectureNameModal').modal('hide');
            
            // 更新页面内容
            $('.card-lesson-title span').text(this.lectureName);
            
            // 通知 animation-creation.js
            if (window.animationCreateApp) {
              window.animationCreateApp.updateLectureName(this.lectureName);
            }
            
            // 保存到服务器
            this.saveLectureNameToServer();
          }
        },
        (error) => {
          console.error('检查课程名称失败:', error);
          this.lectureNameError = '检查课程名称失败，请稍后再试';
        }
      );
    },
    saveLectureNameToServer() {
      ajaxJson(
        '/edutalk/lecture/save-name',
        'POST',
        { 
          name: this.lectureName,
          lecture_id: this.lectureId  // 确保 this.lectureId 是正确的
        },
        (response) => {
          if (response.success) {
            console.log('课程名称已保存到服务器');
          } else {
            console.error('保存课程名称失败:', response.message);
          }
        },
        (error) => {
          console.error('保存课程名称失败:', error);
        }
      );
    },
    createNewLecture() {
      if (!this.newLectureName.trim()) {
        this.lectureNameError = '課程名稱不能為空';
        return;
      }
      
      // 檢查課程名稱是否已存在
      ajaxJson(
        '/edutalk/lecture/check-name',  // 需要在后端创建此路由
        'POST',
        { name: this.newLectureName },
        (response) => {
          if (response.exists) {
            this.lectureNameError = '課程名稱已存在';
          } else {
            // 更新本地数据
            this.lectureName = this.newLectureName;
            this.hackmdURL = '';
            this.videoURL = '';
    
            // 关闭模态框
            $('#addLectureModal').modal('hide');
            
            // 更新页面内容
            $('.card-lesson-title span').text(this.lectureName);
            
            // 更新 HackMD URL 显示
            $('.card-lesson-url a.hackmd-url').text('').attr('href', '#');
            
            // 更新 Video URL 显示
            $('.card-lesson-video-url a.video-url').text('').attr('href', '#');
            
            // 通知 animation-creation.js
            if (window.animationCreateApp) {
              window.animationCreateApp.updateLectureName(this.lectureName);
              window.animationCreateApp.updateHackmdURL('');
              window.animationCreateApp.updateVideoURL('');
            }
            
            // 重置表单
            this.newLectureName = '';
            this.lectureNameError = '';
            
            console.log('新課程名稱已記錄:', this.lectureName);
            
            // 显示成功消息
            this.showMessage($('.success-message#title'));
          }
        },
        (error) => {
          console.error('檢查課程名稱失敗:', error);
          this.lectureNameError = '檢查課程名稱失敗，請稍後再試';
        }
      );
    },
    
    // 添加这个方法来检查课程名称是否已存在
    lectureNameExists(name) {
      // 这里应该根据实际情况来实现检查逻辑
      // 例如，可以检查一个存储所有课程名称的数组
      const existingLectures = [/* 存储现有课程名称的数组 */];
      return existingLectures.includes(name);
    },
    /* ==  Title URL start == */
    showInput(target) {
      $(`.card-lesson-${target}`).hide();
      $(`.card-input-${target}`).show();
    },
    hideInput(target) {
      $(`.card-input-${target}`).hide();
      $(`.card-lesson-${target}`).show();

      if (target === 'title') $('.card-input#title').val(this.lectureName);
      if (target === 'url') $('.card-input#url').val(this.hackmdURL);
      if (target === 'video-url') $('.card-input#video-url').val(this.videoURL);
    },
    renameLecture() {
      if (!this.lectureName.trim()) {
        alert('課程名稱不能為空');
        return;
      }
      
      // 檢查新名稱是否與當前名稱相同
      if (this.lectureName === this.originalLectureName) {
        this.hideInput('title');
        return;
      }
      
      // 檢查課程名稱是否已存在
      ajaxJson(
        '/check-lecture-name',
        'POST',
        { name: this.lectureName },
        (response) => {
          if (response.exists) {
            alert('課程名稱已存在');
            this.lectureName = this.originalLectureName;
          } else {
            // 原有的重命名邏輯
            ajaxJson(
              urls.lecture.rename,
              'POST',
              { name: this.lectureName },
              () => {
                this.originalLectureName = this.lectureName;
                this.hideInput('title');
                this.showMessage($('.success-message#title'));
              },
              (jqXHR) => {
                if (jqXHR.responseJSON !== undefined) {
                  const err = $('.error-message#title');
                  this.showMessage(err);
                  err.text(jqXHR.responseJSON.reason);
                }
              },
            );
          }
        },
        (error) => {
          console.error('檢查課程名稱失敗:', error);
        }
      );
    },
    
    updateLectureUrl() {
      const inputUrl = $('.card-input#url').val();
      if (inputUrl === this.urlHistory[0]) return;
      if (!this.isValidHttpUrl(inputUrl)) {
        const err = $('.error-message#url');
        this.showMessage(err);
        err.text('Invalid URL');
        return;
      }
      ajaxJson(
        urls.lecture.url,
        'POST',
        { url: inputUrl },
        (response) => {
          $('#lesson-url').prop('src', inputUrl);
          this.hackmdURL = inputUrl;
          this.hideInput('url');
          this.showMessage($('.success-message#url'));
          if ('url_history' in response) {
            this.urlHistory = response.url_history;
          }
          // 更新 card.html 上的顯示
          $('.card-lesson-url a.hackmd-url').text(inputUrl).attr('href', inputUrl);
          // 通知 animation-creation.js
          if (window.animationCreateApp) {
            window.animationCreateApp.updateHackmdURL(inputUrl);
          }
        },
        (jqXHR) => {
          if (jqXHR.responseJSON !== undefined) {
            const err = $('.error-message#url');
            this.showMessage(err);
            err.text(jqXHR.responseJSON.reason);
          }
        },
      );
    },
    updateVideoUrl() {
      const inputUrl = $('.card-input#video-url').val();
      if (inputUrl === this.videoHistory[0]) return;
      if (!this.isValidRtspUrl(inputUrl)) {
        const err = $('.error-message#video-url');
        app.showMessage(err);
        err.text('Invalid RTSP URL');
        return;
      }
      ajaxJson(
        urls.lecture.video_url,
        'POST',
        { video_url: inputUrl },
        (response) => {
          app.videoURL = inputUrl;
          animationApp.videoURL = inputUrl;
          app.hideInput('video-url');
          app.showMessage($('.success-message#video-url'));
          if ('video_history' in response) {
            app.videoHistory = response.video_history;
          }
        },
        (jqXHR) => {
          if (jqXHR.responseJSON !== undefined) {
            const err = $('.error-message#video-url');
            app.showMessage(err);
            err.text(jqXHR.responseJSON.reason);
          }
        },
      );
    },
    setUrl(event) {
      if (event) {
        const URL = event.target.text;
        if (!this.isValidHttpUrl(URL)) {
          const err = $('.error-message#url');
          app.showMessage(err);
          err.text('Invalid URL');
          return;
        }
        $('.card-input#url').val(URL);
      }
    },
    setVideoUrl(event) {
      if (event) {
        const URL = event.target.text;
        if (!this.isValidRtspUrl(URL)) {
          const err = $('.error-message#video-url');
          app.showMessage(err);
          err.text('Invalid RTSP URL');
          return;
        }
        $('.card-input#video-url').val(URL);
      }
    },
    showMessage(obj) {
      obj.show();
      setTimeout(() => { obj.fadeOut(); }, 1000);
    },
    isValidHttpUrl(string) {
      let url;

      try {
        url = new URL(string);
      } catch (_) {
        return false;
      }

      return url.protocol === 'http:' || url.protocol === 'https:';
    },
    isValidRtspUrl(string) {
      let url;

      try {
        url = new URL(string);
      } catch (_) {
        return false;
      }

      return url.protocol === 'rtsp:';
    },
    confirmDelete() {
      try {
        if (animationApp.replayDA) animationApp.replayDA.dan.deregister();
        if (animationApp.replayM2) animationApp.replayM2.dan.deregister();
      } catch (e) {
        console.error(e);
      }

      window.onbeforeunload();
      ajaxJson(
        urls.lecture.delete,
        'DELETE',
        {},
        (result) => {
          window.onbeforeunload = undefined;
          window.location.href = result.url;
        },
        (jqXHR) => {
          if (jqXHR.responseJSON !== undefined) {
            alert(jqXHR.responseJSON.reason);
          }
        },
      );
    },
    /* ==  Title URL end == */
    /* ==  Physical Feature Binding start == */
    selectDfIv() {
      const index = $('#selected-iv-select option:selected').attr('value');
      this.initSettingIv(index);
    },
    reindexIv() {
      const inIvList = this.ivList.reduce((c, { giv_name: key }) => {
        c[key] = (c[key] || 0) + 1;
        return c;
      }, {});
      const counter = this.ivList.reduce((c, { giv_name: key }) => {
        c[key] = 0;
        return c;
      }, {});
      this.ivList.forEach((iv) => {
        if (inIvList[iv.giv_name] === 1) {
          this.$set(iv, 'index', '');
        } else {
          this.$set(iv, 'index', counter[iv.giv_name] += 1);
        }

        for (const param of iv.params) {
          // restore mac_addr for same model
          this.deviceAddresses[param.model] = param.mac_addr;
          // todo: accept non numeric default
          if (typeof param.default === 'string') {
            param.default = param.default.replace(/^['](.+(?=[']$))[']$/, '$1');
          }
        }

        this.completeParams(iv);
      });

      this.ivList.sort((a, b) => {
        const nameA = a.giv_name.toUpperCase(); // ignore upper and lowercase
        const nameB = b.giv_name.toUpperCase(); // ignore upper and lowercase
        if (nameA < nameB) return -1;
        if (nameA > nameB) return 1;
        return 0; // names must be equal
      });

      this.initSettingIv(0);
    },
    completeParams(iv) {
      iv.params.forEach((param, index) => {
        const { device } = param;
        const { sensor } = param;
        const opt = this.sensorOptions[device][sensor];

        if (opt === undefined) return;

        if (opt.dimension > 1) param.function = `x${index + 1}`;

        if (opt.unit) param.sensor_unit = opt.unit;
      });

      this.$forceUpdate();
    },
    initParam(index) {
      const param = this.settingIv.params[index];
      const option = $(`.sensor-select[index=${index}] option:selected`);
      const { model } = this.settingIv.params[index];
      const mac_addr = this.deviceAddresses[model];
      const device = option.attr('device');
      const sensor = option.attr('sensor') || '';
      const text = option.text();

      param.model = model;
      param.mac_addr = mac_addr;
      param.device = device;
      param.sensor = sensor;
      param.sensor_unit = 'None';
      param.function = '';
      param.type = text === 'Input Box (String)' ? 'string' : '';
      param.default = param.type === 'string' ? `${param.default}` : (Number(param.default) || 0);
      this.completeParams(this.settingIv);

      // the updated function will be fired
    },
    initSettingIv(index) {
      if (!this.ivList[index]) {
        this.settingIv.show = false;
        return;
      }

      if ($('#selected-iv-select option:selected').attr('value') !== index) {
        $('#selected-iv-select').val(index).change();
      }

      this.settingIv.show = true;
      this.settingIv.params = this.ivList[index].params;
      this.settingIv.giv_name = this.ivList[index].giv_name;
      this.settingIv.type = this.ivList[index].type;

      this.completeParams(this.settingIv);
    },
    update() {
      $('#submit-btn').attr('disabled', true);

      try {
        if (animationApp.replayDA) animationApp.replayDA.dan.deregister();
        if (animationApp.replayM2) animationApp.replayM2.dan.deregister();
      } catch (e) {
        console.error(e);
      }

      const ivList = JSON.parse(JSON.stringify(this.ivList));
      for (const iv of ivList) {
        for (const p of iv.params) {
          // accept non numeric default
          if (p.device !== 'Input Box') continue;
          if (p.type === 'string') {
            p.default = iv.type === 'array' ? `${p.default}` : `'${p.default}'`;
          }
        }
      }

      ajaxJson(
        urls.lecture.physical,
        'PUT',
        {
          odm: {
            name: this.odm,
            dfs: this.odfs,
          },
          idm: {
            name: this.idm,
            dfs: this.idfs,
          },
          joins: this.joins,
          iv_list: ivList,
        },
        (result) => {
          console.log(Date.now(), ' success');
          window.location.href = result.url;
        },
        (jqXHR) => {
          $('#submit-btn').attr('disabled', false);
          if (jqXHR.responseJSON !== undefined) {
            app.err.type = jqXHR.responseJSON.type;
            app.err.msg = jqXHR.responseJSON.reason;
          }
        },
      );
    },
    /* ==  Physical Feature Binding end == */
    updateActuatorVars() {
      $('#submit-actuator-vars-btn').attr('disabled', true);

      try {
        if (animationApp.replayDA) animationApp.replayDA.dan.deregister();
        if (animationApp.replayM2) animationApp.replayM2.dan.deregister();
      } catch (e) {
        console.error(e);
      }

      ajaxJson(
        urls.lecture.actuator,
        'PUT',
        {
          output_variables: this.output_variables,
        },
        (result) => {
          console.log(Date.now(), ' success');
          window.location.href = result.url;
        },
        (jqXHR) => {
          $('#submit-actuator-vars-btn').attr('disabled', false);
          if (jqXHR.responseJSON !== undefined) {
            app.err.type = jqXHR.responseJSON.type;
            app.err.msg = jqXHR.responseJSON.reason;
          }
        },
      );
    },
    updateSensors() {
      const { giv_name } = this.settingIv;
      this.settingIv.params.forEach((param, index) => {
        const sensorSelect = $(`.sensor-select[index=${index}]`);
        const deviceModel = this.settingIv.params[index].model;

        const sensorOptions = {};
        sensorOptions[deviceModel] = this.sensorOptions[deviceModel];
        if (deviceModel === 'Smartphone') {
          sensorOptions['Range Slider'] = this.sensorOptions['Range Slider'];
          sensorOptions['Input Box (Number)'] = this.sensorOptions['Input Box'];
          sensorOptions['Input Box (String)'] = this.sensorOptions['Input Box'];
          sensorOptions.Morsensor = this.sensorOptions.Morsensor;
        }

        sensorSelect.empty();
        sensorSelect.append($('<option>', { text: 'Please select one', disabled: true }));
        for (const device in sensorOptions) {
          if (sensorOptions[device].dimension) {
            sensorSelect.append($('<option>', {
              device: device.startsWith('Input Box') ? 'Input Box' : device,
              text: `${device}`,
            }));
          } else {
            for (const sensor in sensorOptions[device]) {
              if (Object.prototype.hasOwnProperty.call(sensorOptions[device], sensor)) {
                sensorSelect.append($('<option>', {
                  device,
                  sensor,
                  text: `${sensor}${device === 'Morsensor' ? `(${device})` : ''}`,
                }));
              }
            }
          }
        }

        const { device } = param;
        const { sensor } = param;
        const type = param.type === 'string' ? 'String' : 'Number';
        const pre = $(`.sensor-select[index=${index}] option:selected`);
        pre.removeAttr('selected');
        if (device === 'Input Box') {
          $(`.sensor-select[index=${index}] option[device='${device}']:contains('(${type})')`).prop('selected', true);
        } else if (sensor) {
          $(`.sensor-select[index=${index}] option[device='${device}'][sensor='${sensor}']`).prop('selected', true);
        } else {
          $(`.sensor-select[index=${index}] option[device='${device}']`).prop('selected', true);
        }
      });
    },
  },
  // Ref: https://v2.vuejs.org/v2/api/#mounted
  mounted() {
    const path = window.location.pathname;
  const parts = path.split('/');
  this.lectureId = parts[parts.length - 1];
    $('#lectureNameModal').modal('show');
    document.getElementById('addNewLectureLink').addEventListener('click', (e) => {
      e.preventDefault();
      this.newLectureName = '';
      this.lectureNameError = '';
      $('#addLectureModal').modal('show');
    });
    this.$nextTick(function () {
      // Code that will run only after the entire view has been rendered
      this.reindexIv();
      $('.error-message#title').hide();
      $('.error-message#url').hide();
      $('.error-message#video-url').hide();
    });
  },
  // Ref: https://v2.vuejs.org/v2/api/#updated
  updated() {
    this.updateSensors();
  },
});
