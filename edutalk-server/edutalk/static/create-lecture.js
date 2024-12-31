/* global tList:false unitList:false globalIvList:false ajaxJson:false actuatorVarList:false */

Vue.options.delimiters = ['[[', ']]'];
const app2 = new Vue({
  el: '#new-card',
  data: {
    lectureName: '',
    url: '',
    odm: '',
    vpTemplate: 'New',
    tList,
    output_variables: [],
    selectedActuatorVar: 0,
    /*
    output_variables: [
          {
            'key': var_name, # place holder for count, ex. Color
            'name': name of variable # ex. Color, Color1, ...
            'type': type of var, # value, array, or vector depends on dim
            'dim': num of dimension,
            'default': [...],
            'actuator': dm name of actuator, # can be empty
            'odf': odf name of actuator, # can be empty
            'mac_addr': mac addr of actuator da, # can be empty
          }, ...
    ]
    */
    actuatorVarList,
    unitList,
    /* globalIvList: {
        iv_name: {
          selected: user's chosen,
          frequency: frequency of user choose this giv // default is 0
        }
      }

      ivList: [{
        giv_name: name of a global input variable,
        type: type of variable,
        index:   ''  , if no duplicate giv_name
              integer, otherwise
        params: [{
          'device': Range Slider or Input Box or Smartphone or Morsensor
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
        params: iv.params
      }
    */
    globalIvList,
    ivList,
    settingIv: {
      show: false,
      giv_name: '',
      type: { key: '' },
      index: '',
      params: [],
    },
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
            default: // Smartphone and Morsensor
              idf.name = `Edu${param.sensor.slice(0, 3)}-I`;
          }

          odf.unit.push(param.unit);
          odf.type.push(param.type);

          joins[odf.name].push([idf.name, param.function, param.default]);

          if (smSensorList.includes(param.sensor)) return;

          if (param.device === 'Smartphone' || param.device === 'Morsensor') smSensorList.push(param.sensor);

          idfs.push(idf);
        });

        odfs.push(odf);
      });

      return [odfs, idfs, joins];
    },
    odfs() { return this.dfs[0]; },
    idfs() { return this.dfs[1]; },
    joins() { return this.dfs[2]; },
    paramsLen: {
      get() {
        return this.settingIv.params.length;
      },
      set(value) {
        if (value > 9) value = 9;
        if (value <= 0) value = 1;

        this.err.type = '';
        this.err.msg = '';

        const old = this.settingIv.params.length;
        if (old < value) this.settingIv.params.push(newParam());
        if (old > value) this.settingIv.params.pop();
        this.settingIv.type.key = value == 1 ? 'value' : 'array';
      },
    },
    actuatorVarLen: {
      get() {
        return this.output_variables[this.selectedActuatorVar].default.length;
      },
      set(value) {
        if (value > 3) value = 3;
        if (value <= 0) value = 1;

        this.err.type = '';
        this.err.msg = '';

        const defaults = this.output_variables[this.selectedActuatorVar].default;
        const old = defaults.length;
        if (old < value) defaults.push(0);
        if (old > value) defaults.pop();
        this.output_variables[this.selectedActuatorVar].dim = value;
        this.output_variables[this.selectedActuatorVar].type = value == 1 ? 'value' : 'array';
      },
    },
    frequencyOfGiv() {
      const sortable = [];
      for (const giv in globalIvList) {
        if (Object.prototype.hasOwnProperty.call(globalIvList, giv)) {
          sortable.push([giv, globalIvList[giv].frequency]);
        }
      }

      sortable.sort((a, b) => b[1] - a[1]);
      return sortable.slice(0, 5);
    },
  },
  // self-defined function for this vue object
  methods: {
    changeTemplate() {
      const selectedTemp = this.vpTemplate;
      const templateIvList = this.tList[selectedTemp].iv_list.reduce((c, { giv_name: key }) => {
        c[key] = (c[key] || 0) + 1;
        return c;
      }, {});
      for (const giv in this.globalIvList) {
        if (Object.prototype.hasOwnProperty.call(this.globalIvList, giv)) {
          globalIvList[giv].selected = templateIvList[giv] || 0;
        }
      }
      this.ivList = this.tList[selectedTemp].iv_list.slice();
      this.reloadIvManage();
    },
    selectDfIv() {
      this.err.type = '';
      this.err.msg = '';

      const index = $('#selected-iv-select option:selected').attr('value');
      this.initSettingIv(index);
    },
    reloadIvManage() {
      const inIvList = this.ivList.reduce((c, { giv_name: key }) => {
        c[key] = (c[key] || 0) + 1;
        return c;
      }, {});

      for (const giv in this.globalIvList) {
        if (Object.prototype.hasOwnProperty.call(this.globalIvList, giv)) {
          const { selected } = this.globalIvList[giv];
          const current = (inIvList[giv] || 0);
          const diff = selected - current;
          if (diff > 0) { // need to add some iv
            for (let i = 0; i < diff; i += 1) {
              const iv = {};
              iv.giv_name = giv;
              iv.type = { key: 'value' };
              iv.params = [newParam()];
              this.ivList.push(iv);
            }
          }
          if (diff < 0) { // need to remove some iv
            const notSameGiv = $.grep(this.ivList, (iv) => iv.giv_name !== giv);
            const sameGiv = $.grep(this.ivList, (iv) => {
              let { index } = iv;
              if (index === '') index = 1;
              return iv.giv_name === giv && index <= selected;
            });
            this.ivList = notSameGiv.concat(sameGiv);
          }
        }
      }

      this.reindexIv();
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
      iv.params.forEach((param) => {
        if (param.sensor_unit === undefined) param.sensor_unit = 'None';
        if (param.min === undefined) param.min = 0;
        if (param.max === undefined) param.max = 10;
        if (param.default === undefined) param.default = 5;
        if (param.unit === undefined) param.unit = 'None';
        if (param.type === undefined) param.type = 'float';
      });
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
    },
    addNewIv() {
      let newIvName = '';
      while (true) {
        newIvName = prompt('Please enter a new variable name: ');
        if (!newIvName) {
          return;
        }
        if (newIvName === 'add new variable' || !newIvName.trim()) {
          alert('Invalid name, english alphabet or number or _ only');
          continue;
        }
        if (newIvName in this.globalIvList) {
          alert('Duplicate name');
          continue;
        }
        break;
      }

      ajaxJson(
        urls.lecture.iv,
        'PUT',
        { name: newIvName },
        () => {
          app2.$set(app2.globalIvList, newIvName, { selected: 0, frequency: 0 });
          app2.reloadIvManage();
          console.log(`Add new global iv '${newIvName}' success`);
        },
        (jqXHR) => {
          if (jqXHR.responseJSON !== undefined) {
            alert(jqXHR.responseJSON.reason);
          }
          app2.addNewIv();
        },
      );
    },
    addNewOv() {
      let newOvName = '';
      while (true) {
        newOvName = prompt('Please enter a new variable name: ');
        if (!newOvName) {
          return;
        }
        if (newOvName === 'add new variable' || !newOvName.trim()) {
          alert('Invalid name, english alphabet or number or _ only');
          continue;
        }
        if (this.actuatorVarList.includes(newOvName)) {
          alert('Duplicate name');
          continue;
        }
        break;
      }

      ajaxJson(
        urls.lecture.ov,
        'PUT',
        { name: newOvName },
        () => {
          app2.$set(app2.actuatorVarList, app2.actuatorVarList.length, newOvName);
          console.log(`Add new global ov '${newOvName}' success`);
        },
        (jqXHR) => {
          if (jqXHR.responseJSON !== undefined) {
            alert(jqXHR.responseJSON.reason);
          }
          app2.addNewOv();
        },
      );
    },
    addNewUnit(index) {
      if (this.settingIv.params[index].unit === 'add new unit') {
        let newUnitName = '';
        while (true) {
          newUnitName = prompt('Please enter a new unit name: ');
          if (!newUnitName) {
            this.settingIv.params[index].unit = 'None';
            return;
          } if (newUnitName === 'add new unit' || !newUnitName.trim()) {
            alert('invalid unit name');
          } else {
            break;
          }
        }

        ajaxJson(
          urls.lecture.unit,
          'PUT',
          { name: newUnitName },
          () => {
            app2.unitList.push(newUnitName);
            app2.settingIv.params[index].unit = newUnitName;
            console.log(`Add new unit '${newUnitName}' success`);
          },
        );
      }
    },
    checkDimensions() {
      for (let i = 0; i < this.ivList.length; i += 1) {
        const iv = this.ivList[i];
        if (iv.params.length === 0) {
          this.err.type = 'df';
          this.err.msg = 'Dimensions cannot be 0.';
          this.initSettingIv(i);
          return false;
        }
      }
      this.err.type = '';
      this.err.mag = '';

      return true;
    },
    checkUrl() {
      if (this.isValidHttpUrl()) {
        this.err.type = '';
        this.err.mag = '';
      } else {
        this.err.type = 'url';
        this.err.msg = 'Invalid URL';
      }
    },
    isValidHttpUrl() {
      if (this.url === '') return true;

      let url;
      try {
        url = new URL(this.url);
      } catch (_) {
        return false;
      }

      return url.protocol === 'http:' || url.protocol === 'https:';
    },
    reloadActuatorManage(actuatorVar, event) {
      const selected = this.output_variables.filter((a) => a.key === actuatorVar);
      const diff = event.target.value - selected.length;
      if (diff > 0) {
        for (let i = 1; i <= diff; i++) {
          this.output_variables.push({
            key: actuatorVar,
            dim: 1,
            name: actuatorVar + (selected.length + i),
            type: 'value',
            default: [0],
            actuator: '',
            odf: '',
            mac_addr: '',
          });
        }
        if (event.target.value == 1) {
          this.output_variables.find((a) => a.key === actuatorVar).name = actuatorVar;
        } else if (event.target.value > 1) {
          this.output_variables.find((a) => a.key === actuatorVar).name = `${actuatorVar}1`;
        }
        this.reIndexSelectedActuator();
      } else if (diff < 0) {
        let count = 0;
        this.output_variables = this.output_variables.filter((a) => {
          if (a.key === actuatorVar) {
            if (count < event.target.value) {
              if (count == 0 && event.target.value == 1) a.name = actuatorVar;
              count++;
              return true;
            }
            return false;
          }
          return true;
        });
        this.reIndexSelectedActuator();
      }
    },
    reIndexSelectedActuator() {
      this.output_variables.sort((a, b) => {
        const nameA = a.name.toUpperCase(); // ignore upper and lowercase
        const nameB = b.name.toUpperCase(); // ignore upper and lowercase
        if (nameA < nameB) return -1;
        if (nameA > nameB) return 1;
        return 0; // names must be equal
      });
      this.selectedActuatorVar = 0;
    },
    selectActuatorVar() {
      this.err.type = '';
      this.err.msg = '';

      this.selectedActuatorVar = $('#selected-actuator-select option:selected').attr('value');
    },
    create() {
      if (!this.checkDimensions()) return;
      if (!this.isValidHttpUrl()) return;

      $('#submit-btn').attr('disabled', true);

      const ivList = JSON.parse(JSON.stringify(this.ivList));
      for (const iv of ivList) {
        // extract type key
        iv.type = iv.type.key;

        for (const p of iv.params) {
          // accept non numeric default
          const d = parseFloat(p.default);
          if (isNaN(d)) {
            p.device = 'Input Box';
            p.default = iv.type === 'array' ? `${p.default}` : `'${p.default}'`;
            p.type = 'string';
          } else {
            p.default = d;
          }
          // auto scale min max
          if (p.device === 'Range Slider') {
            if (p.default >= 0) {
              p.min = 0;
              p.max = 10 ** (`${p.default}`).length;
            } else {
              p.min = -(10 ** ((`${p.default}`).length - 1));
              p.max = 0;
            }
          }
        }
      }
      
      for (const key in this.joins) {
        if (this.joins.hasOwnProperty(key)) {
            const array = this.joins[key];
            for (const subArray of array) {
                if (subArray.length === 3) {
                    try {
                        subArray[2] = parseFloat(subArray[2]);
                        if(isNaN(subArray[2])){
                          subArray[2]=subArray[2].toString();
                        }
                    } catch (error) {
                        console.error('Parsing Joins Failed: ', error);
                    }
                }
            }
        }
      }

      const output_variables = JSON.parse(JSON.stringify(this.output_variables));
      for (const ov of output_variables) {
        // accept non numeric default
        const ds = ov.default;
        for (let i = 0; i < ds.length; i++) {
          const d = parseFloat(ds[i]);
          if (!isNaN(d)) ds[i] = d;
          else if (ov.type != 'array') ds[i] = `'${ds[i]}'`;
        }
      }

      ajaxJson(
        urls.lecture.create,
        'PUT',
        {
          name: this.lectureName,
          url: this.url,
          odm: {
            name: this.odm,
            dfs: this.odfs,
          },
          idm: {
            name: this.idm,
            dfs: this.idfs,
          },
          joins: this.joins,
          code: this.vpTemplate,
          iv_list: ivList,
          output_variables,
        },
        (result) => {
          console.log(Date.now(), ' success');
          window.location.href = result.url;
        },
        (jqXHR) => {
          $('#submit-btn').attr('disabled', false);
          if (jqXHR.responseJSON !== undefined) {
            app2.err.type = jqXHR.responseJSON.type;
            app2.err.msg = jqXHR.responseJSON.reason;
          }
        },
      );
    },
  },
  // Ref: https://v2.vuejs.org/v2/api/#mounted
  mounted() {
    this.$nextTick(function () {
      // Code that will run only after the entire view has been rendered
      this.reloadIvManage();
      $('.float-label').each(function () {
        const input = $(this).find('input, select');
        const label = $(this).find('label');
        input.focus(() => {
          input.next().addClass('active');
        });
        input.blur(() => {
          if (input.val() === '' || input.val() === 'blank') {
            label.removeClass();
          }
        });
      });
    });
  },
});

function newParam() {
  return {
    model: 'Smartphone',
    mac_addr: '',
    device: 'Range Slider',
    sensor: '',
    sensor_unit: 'None',
    min: 0,
    max: 10,
    default: 0,
    unit: 'None',
    type: 'float',
    function: '',
  };
}
