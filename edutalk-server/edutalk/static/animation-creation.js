// 首先添加一個臨時的 QRCode 構造函數
window.QRCode = function(element, options) {
  console.log('Temporary QR Code constructor');
  return {
    clear: function() {},
    makeCode: function(text) {
      console.log('Making QR code for:', text);
    }
  };
};
const animationCreateApp = new Vue({
  el: '#animation-creation',
  data: {
    lastAnimationCode: '',
    //needsSceneRefresh: false,
    lastPrompt: '',
    isProcessingModification: false,
    csrfToken: document.querySelector('meta[name="csrf-token"]').getAttribute('content'),
    currentType: 'value',
    promptPlaceholder: '',
    errorMessages: [], // 存儲每輪的錯誤消息
  generatedCodes: [], // 存儲每輪生成的代碼
  rcUrl: null,
  token: null,
  _cachedRcUrl: null,
    ERROR_STATES: {
      INITIAL_ERROR: 'INITIAL_ERROR',
      FIXING: 'FIXING', 
      MAX_ATTEMPTS: 'MAX_ATTEMPTS'
    },
    fixAttempts: 0,
  maxFixAttempts: 10,
    lectureName: typeof lectureName !== 'undefined' ? lectureName : '',
    hackmdURL: typeof hackmdURL !== 'undefined' ? hackmdURL : '',
    lecture: typeof lecture !== 'undefined' ? lecture : null,
    programName: typeof daName !== 'undefined' ? daName : '',
    showSubmitButton: false,
    defaultGptPrompt: '',
    isGenerating: false,
    generatedCode: '',
    isFromCyberSetup: false,
    vpTemplate: '',
    tList: {},  // 將從後端獲取的模板列表存儲在這
    selectedIDF: {
      name: '',
      dimensions: 1,
      type: 'value'
    },
    experimentDescription: '',
    cyberVarSetupInfo: '',
    lectureId: '',
    numberOfDimensions: 1,
    showIDFModal: false,
    showSensorModal: false,
    settingIv: {
      type: ''
    },
    selectedIDFs: {},
    numberOfDimensions: 1,
    newVariableName: '',
    selectedDefaultValues: {},
    idfVariables: [
      "Angle_I", "Elasticity_I", "Friction_I", "Gravity_I", "Gyroscope_I",
      "Height_I", "Humidity_I", "Length_I", "Luminance_I", "Magnetometer_I",
      "Mass_I", "Number_I", "Orientation_I", "Power_I", "Radius_I",
      "Restitution_I", "Speed_I", "UV_I", "Velocity_I"
    ],
    currentVariable: '',
    globalIvList: {}, 
    showRuntimeError: false,
    currentSessionId: null,
    selectedSessionId: '',
    cyberVariables: [],
    currentMode: '',
    selectedSerialNumber: '',
    sessionIds: [],
    serialNumbers: [],
    isSubmitDisabled: true,
    lectureName,
    fixingMessage: '',
    gptPrompt: '',
    vpythonCode: '',
    defaultVpythonCode: '',
    isSubmittingToGpt: false,
    isLoadingHackMD: true,
    gptResponse: null,
    editLectureName: false,
    editHackmdURL: false,
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
    isFixingError: false,
    needRewrite: false,
    manualSubmit: false,
    ivList,
    deviceAddresses: Object.fromEntries(
      Object.entries(sensorOptions)
        .filter(([k]) => k !== 'Input Box' && k !== 'Range Slider' && k !== 'Morsensor')
        .map(([k]) => [k, '']),
    ),
    err: {
      type: '',
      msg: '',
    },
    vpythonEditor: null,
    debugMode: false,
    autoRedirectEnabled: true,
  },
  created() {
    console.group('Vue Instance Lifecycle');
    console.log('Created hook - Setting up error handling');
    
    this.setupErrorHandling();
    
    console.log('Error handling setup complete');
    console.groupEnd();
  },
  
  beforeDestroy() {
    console.log('Cleaning up error event listener');
    window.removeEventListener('vpython-error', this.handleVpythonError);
  },
  watch: {
    // 監聽 token 變化
    token(newToken) {
      console.log('Token changed:', newToken);
      if (newToken) {
        this.updateRcUrl();
      }
    },
  
    numberOfDimensions(newVal) {
      this.updateTypeSelectorWithForceUpdate();
    },
    gptPrompt(newValue) {
      const marker = "Create a VPython animation to illustrate the following physics experiment:";
      const index = newValue.indexOf(marker);
      
      if (index !== -1) {
        this.experimentDescription = newValue.substring(index + marker.length).trim();
        console.log("Updated experiment description:", this.experimentDescription);
      }
      this.isSubmitDisabled = !newValue.trim();
    },
  
    selectedSessionId: {
      handler(newVal) {
        if (newVal) {
          this.fetchSerialNumbers();
        }
      },
      immediate: true
    },
    selectedSerialNumber: {
      handler(newVal) {
        if (newVal) {
          this.fetchLog();
        }
      },
      immediate: true
    }
  },
  computed: {
    /*controlSliderUrl() {
      if (this.token) {
        const pathParts = window.location.pathname.split('/');
        const lectureId = pathParts[pathParts.indexOf('lecture') + 1];
        return `/edutalk/lecture/${lectureId}/rc/?token=${this.token}`;
      }
      return null;
    }
  ,*/
  rcUrl() {
    return this.buildRcUrl();
  },
  controlSliderUrl() {
    return this.rcUrl;
  },
 
    remoteControlUrl() {
      return `${urls.rcIndex}?token=${this.token}`;
    },
    isGptResponse() {
      const marker = "Create a VPython animation to illustrate the following physics experiment:";
      return this.gptPrompt.includes(marker);
    },
    showRenameBtn() {
      return this.isEditMode; 
    },
    showMultipleInputs() {
      return this.currentType !== 'vector';
    },
    isInitialMode() {
      return this.currentMode === 'initial';
    },
    isSubmitDisabled() {
      return this.isLoadingHackMD || this.isSubmittingToGpt || !this.gptPrompt.trim();
    },
  
    availableSensorDevices() {
      const devices = [];
      for (const model in this.sensorOptions) {
        if (model !== 'Input Box' && model !== 'Range Slider' && model !== 'Morsensor') {
          devices.push({
            model: model,
            d_name: `${model} Device`,
            mac_addr: `${model.toLowerCase()}_mac_address`
          });
        }
      }
      return devices;
    },
  },  
 
  mounted() {
    console.log('頁面開始加載...');
    window.animationCreateApp = this;
    
    $(document).ready(function() {
      $('#glowscript').hide();
    
      $('#glowscript').css({
          'display': 'none',
          'visibility': 'hidden'
      });
  });
    // 確保 CSRF token 已設置
  this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  if (!this.csrfToken) {
    console.error('CSRF token not found in meta tag');
  }
    const pathParts = window.location.pathname.split('/');
    const lectureIdIndex = pathParts.indexOf('lecture') + 1;
    this.lectureId = pathParts[lectureIdIndex];
    
    this.initModalListeners();
    
    this.getCurrentLectureId();
    this.getNewToken().then(token => {
      if (token) {
        this.token = token;
        this.updateRcUrl();
      }
    });
    $('#animation-preview-modal').on('hidden.bs.modal', () => {
      this.setPromptPlaceholder();
    });
  
    // QR Code 和控制拉桿初始化
    document.addEventListener('DOMContentLoaded', () => {
      const qrcodeElement = document.getElementById('qrcode');
      if (qrcodeElement) {
        const qr = new QRCode(qrcodeElement, {
          text: "Live Data URL",
          width: 249,
          height: 249
        });
      }
  
      const controlSlider = document.getElementById('control-slider');
      if (controlSlider) {
        controlSlider.src = remoteControlUrl + "?token=你的控制介面token";
      }
    });
    $('#animation-preview-modal').on('hidden.bs.modal', () => {
      this.onPreviewModalClose();
  });
    const promptElement = document.querySelector('.prompt-container [contenteditable="true"]');
    if (promptElement) {
      promptElement.addEventListener('input', (event) => {
        this.gptPrompt = event.target.textContent;
        this.onPromptChange();
      });
    }
    
  
    console.log('Setting up vpython-error event listener');
  
    window.addEventListener('vpython-error', async (event) => {
      console.log('=============== Received Error Event ===============');
      console.log('Error received in animation-creation.js:', event.detail);
      console.log('Current fix attempts:', this.fixAttempts);
      console.log('================================================');
      
      const { error, code } = event.detail;
      await this.handleExecutionError(new Error(error), code);
    });
    // 檢查來源並保持 prompt
    this.isFromCyberSetup = localStorage.getItem('isFromCyberSetup') === 'true';
    console.log('isFromCyberSetup 狀態:', this.isFromCyberSetup);
    
    // 移除 this.gptPrompt = '' 避免清空已有的 prompt
    this.isLoadingHackMD = false;
    
    if (!this.isFromCyberSetup) {
      console.log('正常進入頁面 - 顯示課程名稱輸入對話框');
      $('#addLectureModal').modal('show');
    } else {
      console.log('從 Cyber Setup 進入 - 跳過課程名稱輸入');
      this.showSubmitButton = true;
      // 確保先載入已儲存的完整 prompt
      this.fetchHackMDContentAndGeneratePrompt();
    }
    
    localStorage.removeItem('isFromCyberSetup');
    this.initializeBasicSettings();
},
  methods: {
    getCurrentLectureId() {
      const pathParts = window.location.pathname.split('/');
      const lectureIdIndex = pathParts.indexOf('lecture') + 1;
      this.lectureId = pathParts[lectureIdIndex];
    },
     
  debugToken() {
    console.group('Token Debug Information');
    console.log('Current Token:', this.token);
    console.log('RC URL:', this.rcUrl);
    console.log('Control Slider URL:', this.controlSliderUrl);
    console.log('Lecture ID:', this.lectureId);
    console.log('CSRF Token:', document.querySelector('meta[name="csrf-token"]').getAttribute('content'));
    console.groupEnd();
},
async fetchHackMDContentAndGeneratePrompt() {
  try {
    this.isLoadingHackMD = true;

    if (!this.hackmdURL) {
      console.log('HackMD URL 為空，無法生成 prompt');
      this.gptPrompt = '';
      this.isLoadingHackMD = false;
      return;
    }

    // 檢查是否是從 Cyber Setup 來的刷新
    const shouldIncludeMapping = this.isFromCyberSetup && localStorage.getItem('cyberInputMappingInfo');

    // 使用 Promise 包裝 ajaxJson
    const fetchMarkdown = () => new Promise((resolve, reject) => {
      ajaxJson(
        `/edutalk/lecture/${this.lectureId}/hackmd/markdown${shouldIncludeMapping ? '?include_mapping=true' : ''}`,
        'GET',
        null,
        (data) => {
          resolve(data);
        },
        (jqXHR) => {
          reject(new Error(jqXHR.responseJSON?.error || 'Failed to fetch markdown'));
        }
      );
    });

    // 嘗試從本地存儲恢復
    if (this.isFromCyberSetup) {
      const storedPrompt = localStorage.getItem('lastPrompt');
      if (storedPrompt) {
        this.gptPrompt = storedPrompt;
        console.log('Restored prompt from local storage');
      }
    }

    try {
      const data = await fetchMarkdown();
      
      if (!data || !data.markdown) {
        throw new Error('Invalid response format');
      }

      const fetchedMarkdown = data.markdown;
      console.log('Successfully fetched Markdown content');

      // 如果是從 Cyber Setup 進入且已有完整的 prompt，則保留
      if (this.isFromCyberSetup && 
          this.gptPrompt && 
          this.gptPrompt.includes('Cyber Input Variable Mapping')) {
        console.log('Keeping existing prompt with mapping info');
        return;
      }

      // 更新 prompt
      this.gptPrompt = fetchedMarkdown;
      localStorage.setItem('lastPrompt', this.gptPrompt);

      // 如果需要提交到 GPT
      if (this.gptPrompt && !this.isFixingError) {
        await this.submitToGPT(this.gptPrompt);
      }
    } catch (error) {
      console.error('Error in markdown fetch:', error);
      
      // 如果本地存儲中有內容，繼續使用
      if (this.isFromCyberSetup && this.gptPrompt) {
        console.log('Using stored prompt after fetch error');
        return;
      }
      
      throw error;
    }

  } catch (error) {
    console.error("處理 Markdown 並提交給 GPT 時發生錯誤:", error);
    // 只在沒有成功恢復本地存儲的情況下顯示錯誤
    if (!this.gptPrompt) {
      this.gptPrompt = `Error: ${error.message}`;
    }
  } finally {
    this.isLoadingHackMD = false;
    console.log("HackMD 內容獲取完成");
  }
},

// 新增提交到 GPT 的輔助方法
async submitToGPT(prompt) {
  try {
    return new Promise((resolve, reject) => {
      ajaxJson(
        `/edutalk/lecture/${this.lectureId}/submit_to_gpt`,
        'POST',
        {
          prompt: prompt,
          mode: 'initial'
        },
        (result) => {
          if (result && result.program) {
            this.updateGeneratedProgram(result.program);
            resolve(result);
          } else {
            reject(new Error('Invalid GPT response'));
          }
        },
        (jqXHR) => {
          reject(new Error(jqXHR.responseJSON?.error || 'GPT request failed'));
        }
      );
    });
  } catch (error) {
    console.error('GPT API Error:', error);
    // 不讓 GPT 錯誤影響整個流程
  }
},
async getNewToken() {
  try {
    const response = await fetch(`/edutalk/lecture/${this.lectureId}/rc/token`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': this.csrfToken
      },
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.token;
  } catch (error) {
    console.error('Error getting token:', error);
    return null;
  }
},
buildRcUrl() {
  if (this.token) {
    return `https://emily.iottalk.tw/edutalk/lecture/${this.lectureId}/rc/?token=${this.token}`;
  }
  return null;
},
// Modify the updateRcUrl method
updateRcUrl() {
  const url = this.buildRcUrl();
  if (!url) return;

  this.rcUrl = url;
  
  // 安全地調用這些方法
  try {
    if (typeof this.updateControlPanel === 'function') {
      this.updateControlPanel(url);
    }
    
    if (typeof this.updateQrCode === 'function') {
      this.updateQrCode(url);
    }
  } catch (error) {
    console.warn('Error updating RC components:', error);
  }
},
updateControlPanel(url) {
  const controlPanel = document.getElementById('control-panel');
  if (controlPanel) {
    controlPanel.src = url;
    console.log('Control panel iframe src updated to:', url);
  } else {
    console.warn('Control panel iframe not found in DOM');
  }
},
    updateControlSlider() {
      if (!this.token) {
        console.warn('No token available for control slider');
        return;
      }

      const controlSlider = document.getElementById('control-slider');
      if (controlSlider) {
        controlSlider.src = this.rcUrl;
        console.log('Updated control slider URL:', this.rcUrl);
      }

      // 同時更新 QR code
      const qrcodeElement = document.getElementById('qrcode');
      if (qrcodeElement) {
        qrcodeElement.innerHTML = ''; // 清除現有的 QR code
        new QRCode(qrcodeElement, {
          text: window.location.origin + this.rcUrl,
          width: 249,
          height: 249
        });
      }
    },
    debugToken() {
      console.group('Token Debug Information');
      console.log('Current Token:', this.token);
      console.log('RC URL:', this.rcUrl);
      console.log('Control Slider URL:', this.controlSliderUrl);
      console.log('Lecture ID:', this.lectureId);
      console.log('CSRF Token:', document.querySelector('meta[name="csrf-token"]').getAttribute('content'));
      console.groupEnd();
    },
    initModalListeners() {
      $('#animation-preview-modal').on('show.bs.modal', () => {
        console.log('Modal is about to show');
        // 確保在 modal 顯示時更新 control slider
        this.updateControlSlider();
      });

      $('#animation-preview-modal').on('shown.bs.modal', () => {
        console.log('Modal is shown');
        // 在 modal 完全顯示後再次確認更新
        this.updateControlSlider();
      });
    }
  ,
    handleControlPanelLoad() {
      console.log('Control panel iframe loaded successfully');
      this.checkRcConnection();
    },
  
    handleControlPanelError(error) {
      console.error('Control panel iframe failed to load:', error);
    },
  
    async checkRcConnection() {
      if(this.debug) {
        console.group('RC Connection Check');
        console.log('Checking RC URL:', this.rcUrl);
      }
  
      try {
        const response = await fetch(this.rcUrl);
        const data = await response.text();
        
        if(this.debug) {
          console.log('RC Response status:', response.status);
          console.log('RC Response headers:', Object.fromEntries([...response.headers]));
          console.log('RC Response data:', data.substring(0, 200) + '...'); // 只顯示前200字符
        }
  
      } catch(err) {
        console.error('RC Connection failed:', err);
      }
  
      if(this.debug) {
        console.groupEnd();
      }
    },
    initializeBasicSettings() {
      this.$nextTick(() => {
        const lectureElement = document.querySelector('.col-sm-2 h5');
        const lectureNameElement = document.querySelector('.lecture-name');
        if (lectureElement && lectureNameElement) {
          const computedStyle = window.getComputedStyle(lectureElement);
          lectureNameElement.style.fontSize = computedStyle.fontSize;
          lectureNameElement.style.fontWeight = computedStyle.fontWeight;
        }
      });
     
      const path = window.location.pathname;
      const parts = path.split('/');
      this.lectureId = parts[parts.length - 1];
      this.csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      
      this.fetchSessionIds().then(() => {
        this.incrementSessionId();
        this.fetchSerialNumbers().then(() => {
          if (this.selectedSerialNumber) {
            this.fetchLog();
          }
        });
      });
      
      this.fetchTemplates();
      this.updateTypeSelectorWithForceUpdate(); 
      this.updateTypeSelector(); 
      this.initVpythonEditor();
    },
    showGeneratedCode(round) {
      const code = this.generatedCodes[round - 1];
      if (code) {
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        modalContent.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: white;
          padding: 30px;
          border-radius: 8px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
          z-index: 1000000;
          width: 80vw;      
          max-height: 80vh;  
          overflow-y: auto;
        `;
        
        modalContent.innerHTML = `
      <h6 style="margin-top: 0; margin-bottom: 20px; font-size: 1.2em;">VPython Code - Round ${round}</h6>
      <pre style="background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 0; font-size: 1.1em;"><code>${code}</code></pre>
      <button onclick="this.closest('.modal-content').remove()" 
              style="position: absolute; top: 15px; right: 15px; border: none; background: none; font-size: 24px; cursor: pointer;">
        ×
      </button>
    `;
        
        document.body.appendChild(modalContent);
      }
    },
    
    setPromptPlaceholder() {
      const promptElement = document.querySelector('.prompt-container [contenteditable="true"]');
      
      if (promptElement && promptElement.isConnected) {
        while (promptElement.firstChild) {
          promptElement.removeChild(promptElement.firstChild);
        }
        
        const placeholder = document.createTextNode('You may manually change the animation\'s behavior by entering the follow-up prompt here. After completion, press the "Create Animation" button.');
        promptElement.appendChild(placeholder);
        promptElement.style.color = '#999';

        const handleFocus = function() {
          if (this.style.color === 'rgb(153, 153, 153)') {
            this.textContent = '';
            this.style.color = '#000';
          }
          this.removeEventListener('focus', handleFocus); 
        };

        promptElement.addEventListener('focus', handleFocus);
      } else {
        console.error('Prompt element not found or not connected to the DOM');
      }
    },
    async checkRcConnection() {
      if(this.debug) {
        console.group('RC Connection Check');
        console.log('Checking RC URL:', this.rcUrl);
      }
  
      try {
        const response = await fetch(this.rcUrl);
        const data = await response.text();
        
        if(this.debug) {
          console.log('RC Response status:', response.status);
          console.log('RC Response headers:', Object.fromEntries([...response.headers]));
          console.log('RC Response data:', data.substring(0, 200) + '...'); // 只顯示前200字符
        }
  
      } catch(err) {
        console.error('RC Connection failed:', err);
      }
  
      if(this.debug) {
        console.groupEnd();
      }
    },
   changeTemplate() {
      // 实现模板更改的逻辑
      console.log('Selected template:', this.vpTemplate);
      // 这里可以添加更多的逻辑，比如根据选择的模板更新其他数据
    },

     async fetchTemplates() {
      try {
        const response = await fetch(`/edutalk/lecture/${this.lectureId}/get_templates`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        this.tList = data;
      } catch (error) {
        console.error("Error fetching templates:", error);
      }
    },

    // 更改模板時的處理函數
    changeTemplate() {
      const selectedTemp = this.vpTemplate;
      if (this.tList[selectedTemp] && this.tList[selectedTemp].iv_list) {
        // 更新 ivList
        this.ivList = this.tList[selectedTemp].iv_list.slice();
        // 可能需要更新其他相關數據
        this.updateIvManage();
      }
    },
    updateHackmdURL(newURL) {
      this.hackmdURL = newURL;
      this.fetchHackMDContentAndGeneratePrompt();
    },
    
    updateLectureName(newName) {
      this.lectureName = newName;
    },
    
    updateVideoURL(newURL) {
      this.videoURL = newURL;
    },
    async unbindDevices() {
      try {
        const response = await fetch(`/edutalk/lecture/${this.lectureId}/vp/unbind/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': this.csrfToken
          }
        });
  
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Failed to unbind devices');
        }
  
        console.log('Devices unbound successfully');
      } catch (error) {
        console.error('Error unbinding devices:', error);
      }
    },
  
    async beforeRouteLeave(to, from, next) {
      await this.unbindDevices();
      next();
    },
    
    async createLecture() {
      console.log('開始創建新課程...');
      
      const nextLectureId = parseInt(this.lectureId) + 1;
      console.log('Next lecture ID:', nextLectureId);
  
      try {
          if (animationApp.replayDA) {
              console.log('註銷 replayDA...');
              animationApp.replayDA.dan.deregister();
          }
          if (animationApp.replayM2) {
              console.log('註銷 replayM2...');
              animationApp.replayM2.dan.deregister();
          }
      } catch (e) {
          console.error('unbind設備出錯:', e);
      }
  
      window.onbeforeunload = function() {};
  
     
      const baseProgramName = `Program${nextLectureId}`;
     
      const randomSuffix = Math.floor(Math.random() * 1000);
      const programName = `${baseProgramName}N${randomSuffix}`; 
      console.log('使用程序名稱:', programName);
      
    
      let idfCounter = 1;
      const idfNameMap = new Map();
      

      const idmDfs = Object.entries(this.selectedIDFs)
          .filter(([_, idf]) => idf !== 'IDF List')
          .map(([variable]) => {
              const ivData = this.globalIvList[variable] || {};
              // 使用純英文數字的名稱
              const idfName = `${programName}I${idfCounter}`; // 簡化 IDF 名稱
              idfNameMap.set(variable, idfName);
              idfCounter++;
              
              return {
                  name: idfName,
                  type: 'float',
                  min: ivData.min || '0',
                  max: ivData.max || '10',
                  default: ivData.default || '5'
              };
          });
  
      // 準備創建課程的數據
      const data = {
          name: this.lecture ? this.lecture.name : this.lectureName,
          url: this.lecture ? this.lecture.url : this.hackmdURL,
          odm: {
              name: programName,
              dfs: this.cyberVariables
                  .filter(v => this.selectedIDFs[v] !== 'IDF List')
                  .map(v => ({
                      // 為 ODF 使用簡單的英文數字名稱
                      name: `${programName}O${this.selectedIDFs[v].replace(/[^a-zA-Z0-9]/g, '')}`,
                      unit: ['None'],
                      type: ['float']
                  }))
          },
          idm: {
              name: `${programName}RC`, 
              dfs: idmDfs
          },
          joins: Object.fromEntries(
              this.cyberVariables
                  .filter(v => this.selectedIDFs[v] !== 'IDF List')
                  .map(v => {
                      const ivData = this.globalIvList[v] || {};
                      const idf = this.selectedIDFs[v];
                      return [
                          `${programName}O${idf.replace(/[^a-zA-Z0-9]/g, '')}`,
                          [[
                              idfNameMap.get(v),
                              '',
                              ivData.default || '5'
                          ]]
                      ];
                  })
          ),
          code: 'New',
          iv_list: this.cyberVariables
              .filter(v => this.selectedIDFs[v] !== 'IDF List')
              .map(v => {
                  const ivData = this.globalIvList[v] || {};
                  return {
                      giv_name: this.selectedIDFs[v],
                      type: 'value',
                      params: [{
                          model: ivData.model || 'Smartphone',
                          mac_addr: '',
                          device: 'RangeSlider', // 移除空格
                          sensor: '',
                          sensor_unit: 'None',
                          min: ivData.min || '0',
                          max: ivData.max || '10',
                          default: ivData.default || '5',
                          unit: 'None',
                          type: 'float',
                          function: ''
                      }],
                      index: ''
                  };
              }),
          output_variables: [],
          id: nextLectureId
      };
  
      // 創建課程
      try {
          const result = await new Promise((resolve, reject) => {
              ajaxJson(
                  urls.lecture.create,
                  'PUT',
                  data,
                  resolve,
                  reject
              );
          });
  
          console.log('新課程創建成功:', result);
          const newUrl = result.url.replace(/\/\d+$/, `/${nextLectureId}`);
          window.location.href = newUrl;
  
      } catch (error) {
          console.error('新課程創建失敗:', error.responseJSON ? error.responseJSON.reason : '未知錯誤');
          
          if (error.responseJSON?.reason?.includes('program name already used')) {
              try {
                  // 生成新的名稱用於重試
                  const newSuffix = Math.floor(Math.random() * 1000);
                  const newProgramName = `${baseProgramName}N${newSuffix}`;
                  
                  // 更新所有相關的名稱，確保只使用英文數字
                  data.odm.name = newProgramName;
                  data.idm.name = `${newProgramName}RC`;
                  
                  // 更新 ODF 名稱
                  data.odm.dfs = data.odm.dfs.map(df => ({
                      ...df,
                      name: `${newProgramName}O${df.name.split('O').pop().replace(/[^a-zA-Z0-9]/g, '')}`
                  }));
                  
                  // 更新 IDF 名稱
                  data.idm.dfs = data.idm.dfs.map((df, index) => ({
                      ...df,
                      name: `${newProgramName}I${index + 1}`
                  }));
                  
                  // 更新 joins 中的名稱
                  const newJoins = {};
                  Object.entries(data.joins).forEach(([key, value]) => {
                      const newKey = `${newProgramName}O${key.split('O').pop().replace(/[^a-zA-Z0-9]/g, '')}`;
                      newJoins[newKey] = value.map(([idfName, ...rest], index) => [
                          `${newProgramName}I${index + 1}`,
                          ...rest
                      ]);
                  });
                  data.joins = newJoins;
  
                  const retryResult = await new Promise((resolve, reject) => {
                      ajaxJson(
                          urls.lecture.create,
                          'PUT',
                          data,
                          resolve,
                          reject
                      );
                  });
  
                  console.log('重試創建成功:', retryResult);
                  const retryUrl = retryResult.url.replace(/\/\d+$/, `/${nextLectureId}`);
                  window.location.href = retryUrl;
  
              } catch (retryError) {
                  console.error('重試創建失敗:', retryError);
                  alert(`創建課程失敗: ${retryError.responseJSON?.reason || '未知錯誤'}`);
              }
          } else {
              alert(error.responseJSON?.reason || '創建課程失敗');
          }
      }
  },
  prepareCreateLectureData(nextLectureId) {
    // 确保 programName 只包含英文字母和数字
    let sanitizedProgramName = `Program${nextLectureId}`;
    
    return {
        name: this.lecture ? this.lecture.name : this.lectureName,
        url: this.lecture ? this.lecture.url : this.hackmdURL,
        odm: {
            name: sanitizedProgramName,
            dfs: this.prepareOdmDfs(nextLectureId),
        },
        idm: {
            name: `${sanitizedProgramName}RC`,
            dfs: this.prepareIdmDfs(nextLectureId),
        },
        joins: this.prepareJoins(nextLectureId),
        code: 'New',
        iv_list: this.prepareIvList(),
        output_variables: [],
        id: nextLectureId
    };
},

prepareOdmDfs(nextLectureId) {
    return this.cyberVariables
      .filter(v => this.selectedIDFs[v] !== 'IDF List')
      .map(v => {
        const idfInfo = this.getIDFInfo(v);
        return {
          name: `Program${nextLectureId}${this.selectedIDFs[v].replace(/\s+/g, '')}-O`,
          unit: Array(idfInfo.dimensions).fill('None'),
          type: Array(idfInfo.dimensions).fill('float')
        };
      });
},

prepareIdmDfs(nextLectureId) {
  // 保存已使用的 IDF 名稱來確保唯一性
  const usedIdfNames = new Set();
  
  return Object.entries(this.selectedIDFs)
      .filter(([_, idf]) => idf !== 'IDF List')
      .map(([variable, idf], index) => {
          const ivData = this.globalIvList[variable] || {};
          const sensor = ivData.sensor || 'RangeSlider';
          let idfName = '';
          let counter = 1;
          
          // 生成唯一的 IDF 名稱
          do {
              idfName = `Program${nextLectureId}${sensor}-I${counter}`;
              counter++;
          } while (usedIdfNames.has(idfName));
          
          usedIdfNames.add(idfName);
          
          return {
              name: idfName,
              type: 'float',
              min: ivData.min || '0',
              max: ivData.max || '10',
              default: ivData.default || '5'
          };
      });
},
  
prepareJoins(nextLectureId) {
  const joins = {};
  // 保存已使用的 IDF 名稱與序號的映射
  const idfNameMap = new Map();
  let counter = 1;
  
  this.cyberVariables
      .filter(v => this.selectedIDFs[v] !== 'IDF List')
      .forEach(v => {
          const ivData = this.globalIvList[v] || {};
          const idf = this.selectedIDFs[v];
          const sensor = ivData.sensor || 'RangeSlider';
          
          if (idf && ivData) {
              // 為每個變量生成唯一的 IDF 名稱
              let idfName = `Program${nextLectureId}${sensor}-I${counter}`;
              idfNameMap.set(v, idfName);
              
              joins[`Program${nextLectureId}${idf}-O`] = [
                  [
                      idfName,
                      '',
                      ivData.default || '5'
                  ]
              ];
              
              counter++;
          }
      });
  
  return joins;
},

    createNewLecture() {
      console.log('開始創建新課程...');
    
      const data = this.prepareCreateLectureData();
      console.log('準備創建的課程數據:', data);
    
      
      ajaxJson(
        urls.lecture.create,
        'PUT',
        data,
        (result) => {
          console.log('新課程創建成功:', result);
          window.location.href = result.url;
        },
        (jqXHR) => {
          console.error('新課程創建失敗:', jqXHR.responseJSON ? jqXHR.responseJSON.reason : '未知錯誤');
          if (jqXHR.responseJSON !== undefined) {
            this.err.type = jqXHR.responseJSON.type;
            this.err.msg = jqXHR.responseJSON.reason;
            alert(`創建課程失敗: ${this.err.msg}`);
          }
        }
      );
    },
    
   
    prepareCreateLectureData() {
      console.log('Preparing lecture data...');
      
      const nextLectureId = this.lectureId + 1;
      const programName = `Program${nextLectureId}`;
      
      // 準備 ODM 數據
      const odmDfs = this.cyberVariables
          .filter(v => this.selectedIDFs[v] !== 'IDF List')
          .map(v => ({
              name: `${programName}${this.selectedIDFs[v].replace(/\s+/g, '')}-O`,
              unit: ['None'],
              type: ['float']
          }));
          
      // 準備 IDM 數據
      const idmDfs = this.prepareIdmDfs(nextLectureId);
      
      // 準備 joins 數據
      const joins = this.prepareJoins(nextLectureId);
      
      // 準備 iv_list 數據
      const ivList = this.cyberVariables
          .filter(v => this.selectedIDFs[v] !== 'IDF List')
          .map(v => {
              const ivData = this.globalIvList[v] || {};
              return {
                  giv_name: this.selectedIDFs[v],
                  type: 'value',
                  params: [{
                      model: 'Smartphone',
                      mac_addr: '',
                      device: ivData.sensor || 'Range Slider',
                      sensor: '',
                      sensor_unit: 'None',
                      min: ivData.min || '0',
                      max: ivData.max || '10',
                      default: ivData.default || '5',
                      unit: 'None',
                      type: 'float',
                      function: ''
                  }],
                  index: ''
              };
          });
  
      return {
          name: this.lecture ? this.lecture.name : this.lectureName,
          url: this.lecture ? this.lecture.url : this.hackmdURL,
          odm: {
              name: programName,
              dfs: odmDfs
          },
          idm: {
              name: `${programName}RC`,
              dfs: idmDfs
          },
          joins: joins,
          code: 'New',
          iv_list: ivList,
          output_variables: [],
          id: nextLectureId
      };
  },
  
  prepareOdmDfs() {
    const currentLectureId = this.lectureId;  // 獲取當前課程ID
    return this.cyberVariables
      .filter(v => this.selectedIDFs[v] !== 'IDF List')
      .map(v => {
        const idfInfo = this.getIDFInfo(v);
        return {
          // 使用當前課程ID構建名稱
          name: `Program${currentLectureId}${this.selectedIDFs[v].replace(/\s+/g, '')}-O`,
          unit: Array(idfInfo.dimensions).fill('None'),
          type: Array(idfInfo.dimensions).fill('float')
        };
      });
  },
  prepareIdmDfs() {
    const currentLectureId = this.lectureId;  // 獲取當前課程ID
    return Object.entries(this.selectedIDFs)
      .filter(([_, idf]) => idf !== 'IDF List')
      .map(([variable, idf]) => {
        const ivData = this.globalIvList[variable] || {};
        const sensor = ivData.sensor || '';
        let dfData = {
          // 使用當前課程ID構建名稱
          name: `Program${currentLectureId}${sensor.replace(/\s+/g, '')}-I1`,
          type: 'float'
        };
  
        if (sensor === 'Range Slider') {
          dfData.min = ivData.min || '0';
          dfData.max = ivData.max || '10';
          dfData.default = ivData.default || '5';
        } else if (sensor === 'Input Box (Number)') {
          dfData.default = ivData.default || '0';
        }
  
        return dfData;
      });
  },
    
  prepareJoins() {
    const currentLectureId = this.lectureId;  // 獲取當前課程ID
    const joins = {};
    this.cyberVariables
      .filter(v => this.selectedIDFs[v] !== 'IDF List')
      .forEach(v => {
        const ivData = this.globalIvList[v] || {};
        const idf = this.selectedIDFs[v];
        const sensor = ivData.sensor || '';
        if (idf && ivData) {
          // 使用當前課程ID構建名稱
          joins[`Program${currentLectureId}${idf}-O`] = [
            [
              `Program${currentLectureId}${sensor.replace(/\s+/g, '')}-I1`,
              '',
              ivData.default || '0'
            ]
          ];
        }
      });
    return joins;
  },
    
    prepareIvList() {
      return this.cyberVariables
        .filter(v => this.selectedIDFs[v] !== 'IDF List')
        .map(v => {
          const ivData = this.globalIvList[v] || {};
          const idf = this.selectedIDFs[v];
          
          return {
            giv_name: idf,
            type: this.getIDFInfo(v).type,
            params: [{
              model: ivData.model || 'Smartphone',
              mac_addr: '',
              device: ivData.sensor || 'Range Slider',
              sensor: '',
              sensor_unit: ivData.sensor_unit || 'None',
              min: ivData.min || '0',
              max: ivData.max || '10',
              default: ivData.default || '5',
              unit: ivData.unit || 'None',
              type: ivData.type || 'float',
              function: ivData.function || ''
            }],
            index: ivData.index || ''
          };
        });
    },
   
    async processFetchedMarkdownAndSubmit() {
      try {
      
        const markdownResponse = await fetch(`/edutalk/lecture/${this.lectureId}/hackmd/markdown`);
        if (!markdownResponse.ok) {
          throw new Error(`HTTP error! status: ${markdownResponse.status}`);
        }
        const data = await markdownResponse.json();
        const fetchedMarkdown = data.markdown;
        
     
        if (!fetchedMarkdown) {
          throw new Error('No markdown content received');
        }
    
        console.log('Fetched Markdown:', fetchedMarkdown);
    
        //const gptApiPrompt = `請用英文敘述下面是在進行何種物理運動, 過濾掉敘述程式撰寫的部分:\n${fetchedMarkdown}`;
        
  
        /*const gptApiResponse = await fetch(`/edutalk/lecture/${this.lectureId}/submit_to_gpt`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': this.csrfToken,
          },
          body: JSON.stringify({
            prompt: fetchedMarkdown,
            mode: 'initial'
          })
        });
    
        if (!gptApiResponse.ok) {
          throw new Error(`HTTP error! status: ${gptApiResponse.status}`);
        }
    
        const gptApiResult = await gptApiResponse.json();*/
        

        const finalPrompt = `
    1. Screen Settings:\n
    Set the canvas width to 700 and height to 400. Do not change the canvas size.\n\n
    2. Object Motion & Parameter Settings:\n
    Create a VPython animation to illustrate the following physics experiment:\n\n
    ${fetchedMarkdown}
        `;
   
        console.log("最終 PROMPT:", finalPrompt);
        this.gptPrompt = finalPrompt;
    
      } catch (error) {
        console.error("Error processing markdown and submitting to GPT:", error);
        this.gptPrompt = `Error: ${error.message}`;
      }
    },
    addNewVariable() {
      if (this.newVariableName && !this.cyberVariables.includes(this.newVariableName)) {
        this.cyberVariables.push(this.newVariableName);
        this.$set(this.selectedIDFs, this.newVariableName, 'IDF 列表');
        this.newVariableName = ''; 
        this.updateModalContent({ program: JSON.stringify({ controlled_variables: this.cyberVariables }) });
      }
    },
    updateIDFButtonText() {
      this.$nextTick(() => {
          console.log(`Attempting to update IDF button text for ${this.currentVariable}`);
          console.log(`Selected IDFs:`, JSON.stringify(this.selectedIDFs));
          
          // 將特殊字符替換為下劃線
          const safeVariableName = this.currentVariable.replace(/\s/g, '_').replace(/[\(\)]/g, ''); // 清理特殊字符
          const buttonSelector = `#idf-btn-${safeVariableName}`;
          console.log(`Button selector:`, buttonSelector);
          
          const idfButton = document.querySelector(buttonSelector);
          console.log('IDF button:', idfButton);
          if (idfButton && this.selectedIDFs[this.currentVariable]) {
              idfButton.textContent = this.selectedIDFs[this.currentVariable];
              console.log(`Updated IDF button text to: ${this.selectedIDFs[this.currentVariable]}`);
          } else {
              console.error('Failed to update IDF button text:', {
                  buttonFound: !!idfButton,
                  selectedIDF: this.selectedIDFs[this.currentVariable],
                  currentVariable: this.currentVariable
              });
          }
      });
  },
  addCheckboxListeners() {
      this.cyberVariables.forEach(v => {
          const checkbox = document.getElementById(v.replace(/\s+/g, ''));
          if (checkbox) {
              checkbox.addEventListener('change', () => this.toggleButtons(v));
          } else {
              console.warn(`Checkbox for variable ${v} not found`);
          }
      });
  },
  updateSensorButtonText() {
    console.log(`Updating Sensor Selection button text for ${this.currentVariable}`);
    const sensorButton = document.querySelector(`#buttons-${this.currentVariable.replace(/\s+/g, '')} button:last-child`);
    if (sensorButton && this.settingIv.params[0] && this.settingIv.params[0].sensor) {
        sensorButton.textContent = this.settingIv.params[0].sensor;
        console.log(`Updated Sensor Selection button text to: ${this.settingIv.params[0].sensor}`);
    } else {
        console.log('Failed to update Sensor Selection button text');
    }
},
    updateTypeSelectorWithForceUpdate() {
      this.updateTypeSelector(); 
      this.$forceUpdate(); 
    },
    updateTypeSelector() {
      console.log(`更新 Type Selector，維度: ${this.numberOfDimensions}`);
    
      if (['Acceleration_I', 'Gyroscope_I', 'Magnetometer_I', 'Orientation_I'].includes(this.selectedIDF.name)) {
        this.settingIv.type = 'vector';
      } else if (this.numberOfDimensions === 1) {
        this.settingIv.type = 'value';
      } else if (this.numberOfDimensions === 3) {
        this.settingIv.type = 'array';
      } else if (this.numberOfDimensions >= 2 && this.numberOfDimensions <= 9) {
        this.settingIv.type = 'array';
      }
    
      console.log(`更新後的類型: ${this.settingIv.type}`);
      this.$forceUpdate(); 
    },
    
    closeIDFDropdown() {
      const dropdown = document.querySelector('.idf-dropdown');
      if (dropdown) {
        dropdown.remove();
      }
    },
    openAddDimensionModal() {
     
      if (this.numberOfDimensions === 1) {
        this.settingIv.type = 'value';
      } else if (this.numberOfDimensions === 3) {
        this.settingIv.type = 'array';
      } else if (this.numberOfDimensions === 2 || (this.numberOfDimensions >= 4 && this.numberOfDimensions <= 9)) {
        this.settingIv.type = 'array';
      }
     
      $('#addDimensionModal').modal('show');
    },  
    saveIDFSelection(idfName) {
      console.log(`Saving IDF selection: ${idfName} for ${this.currentVariable}`);
      
     
      this.$set(this.selectedIDFs, this.currentVariable, idfName);
      console.log('Updated selectedIDFs:', JSON.stringify(this.selectedIDFs));
      
     
      this.updateIDFButtonText();
      
    
      this.closeIDFDropdown();
  
      
      const idfButton = document.querySelector(`#idf-btn-${this.currentVariable.replace(/\s+/g, '')}`);
      if (idfButton) {
          idfButton.textContent = idfName;
          console.log(`Directly updated IDF button text to: ${idfName}`);
      } else {
          console.error(`IDF button not found for ${this.currentVariable}`);
      }
  
     
      this.$nextTick(() => {
          this.updateOdmDfs();
      });
  },
  

  updateOdmDfs() {
      console.log('Updating ODM DFS based on selected IDFs');
     
  },
    saveIDFSelection() {
      const selectedRadio = document.querySelector('input[name="idfVariable"]:checked');
      if (selectedRadio) {
        const idfName = selectedRadio.value;
        this.selectedIDFs[this.currentVariable] = idfName;
        console.log(`Selected IDF: ${idfName}`);
      }
      this.updateIDFButtonText();
      this.closeIDFDropdown();
    },   
    showCyberVariableModal() {
      const modal = document.getElementById('cyberVariableModal');
      modal.removeAttribute('inert');  
      modal.setAttribute('aria-hidden', 'false'); 
      $('#cyberVariableModal').modal('show');
    },
    hideCyberVariableModal() {
      const modal = document.getElementById('cyberVariableModal');
      modal.setAttribute('inert', 'true'); 
      modal.setAttribute('aria-hidden', 'true');  
      $('#cyberVariableModal').modal('hide');
    },
    async connectToCyberVariable() {
      console.log("connectToCyberVariable method called");
      const marker = "Create a VPython animation to illustrate the following physics experiment:";
      const index = this.gptPrompt.indexOf(marker);
  
      if (index !== -1) {
          const experimentDescription = this.gptPrompt.substring(index + marker.length).trim();
          console.log("Extracted experiment description:", experimentDescription);
  
          const prompt = `Identify all the variables that can be controlled in this experiment. Reply with only a JSON array of variable names, like ["var1","var2"]. No other text or formatting.`;
  
          try {
              // 使用 Promise 包裝 ajaxJson 調用
              const submitToGPT = () => new Promise((resolve, reject) => {
                  ajaxJson(
                      `/edutalk/lecture/${this.lectureId}/submit_to_gpt`,
                      'POST',
                      {
                          prompt: prompt,
                          mode: 'initial'
                      },
                      (data) => resolve(data),
                      (jqXHR) => reject(jqXHR)
                  );
              });
  
              const data = await submitToGPT();
              console.log("GPT API Response:", data);
  
              if (data.program) {
                  try {
                      // 移除可能的json前綴和其他非JSON內容
                      let cleanedResponse = data.program
                          .replace(/^json\n/, '')
                          .replace(/```json\n/, '')
                          .replace(/```/, '')
                          .trim();
  
                      // 確保是有效的JSON陣列
                      if (!cleanedResponse.startsWith('[')) {
                          cleanedResponse = `[${cleanedResponse}]`;
                      }
  
                      const parsedVariables = JSON.parse(cleanedResponse);
                      
                      // 過濾變量
                      this.cyberVariables = Array.isArray(parsedVariables) 
                          ? parsedVariables.filter(v => !v.toLowerCase().includes('time') && !v.toLowerCase().includes('duration'))
                          : [];
  
                      console.log("Filtered cyberVariables:", this.cyberVariables);
  
                      // 初始化selectedIDFs
                      this.cyberVariables.forEach(v => {
                          if (!this.selectedIDFs[v]) {
                              this.$set(this.selectedIDFs, v, 'IDF List');
                          }
                      });
  
                      this.updateModalContent(data);
  
                  } catch (error) {
                      console.error('Error parsing GPT response:', error);
                      this.updateModalContent({ 
                          error: 'Failed to parse variables from GPT response'
                      });
                  }
              } else {
                  console.error("No program in GPT response");
                  this.updateModalContent({ 
                      error: 'No valid response from GPT'
                  });
              }
          } catch (error) {
              console.error("Error in GPT API call:", error);
              this.updateModalContent({
                  error: 'Failed to communicate with GPT API'
              });
          }
      } else {
          console.error('Marker text not found in the prompt');
          this.updateModalContent({
              error: 'Invalid prompt format'
          });
      }
  },
    updateModalContent(data) {
      console.log("Updating modal content with data:", data);
    
      const modalBody = document.querySelector('#cyberVariableModal .modal-body');
      if (!modalBody) {
        console.error("Modal body element not found");
        return;
      }
    
      if (data.error) {
        modalBody.innerHTML = `<p class="text-danger">${data.error}</p>`;
        return;
      }
    
      try {
        // 確保cyberVariables是有效的數組
        if (!Array.isArray(this.cyberVariables)) {
          this.cyberVariables = [];
        }
    
        // 先創建臨時容器
        const tempContainer = document.createElement('div');
        
        // 添加標題
        tempContainer.innerHTML = '<p>Controllable Variables:</p>';
    
        // 為每個變量創建元素
        this.cyberVariables.forEach(variable => {
          const variableDiv = document.createElement('div');
          variableDiv.className = 'form-check d-flex align-items-center mb-2';
          
          // 使用安全的ID生成方式
          const safeId = variable.replace(/[^a-zA-Z0-9]/g, '_');
          
          variableDiv.innerHTML = `
            <input class="form-check-input" 
                   type="checkbox" 
                   id="${safeId}"
                   data-variable="${variable}">
            <label class="form-check-label mr-2" 
                   for="${safeId}">${variable}</label>
            <div id="buttons-${safeId}" 
                 style="display: none;"
                 class="variable-buttons">
              <button class="btn btn-sm btn-secondary mr-2 idf-list-btn" 
                      data-variable="${variable}"
                      id="idf-btn-${safeId}">${this.selectedIDFs[variable] || 'IDF List'}</button>
              <button class="btn btn-sm btn-secondary sensor-select-btn" 
                      data-variable="${variable}">Sensor Selection</button>
            </div>
          `;
          
          tempContainer.appendChild(variableDiv);
        });
    
        // 添加"Add new"部分
        const addNewSection = document.createElement('div');
        addNewSection.className = 'form-group mt-3';
        addNewSection.innerHTML = ``;
        tempContainer.appendChild(addNewSection);
    
        // 清空並更新模態框內容
        modalBody.innerHTML = '';
        modalBody.appendChild(tempContainer);
    
        // 重新綁定事件監聽器
        this.$nextTick(() => {
          // 綁定複選框事件
          const checkboxes = modalBody.querySelectorAll('.form-check-input');
          checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
              const variable = e.target.dataset.variable;
              this.toggleButtons(variable);
            });
          });
    
          // 綁定IDF按鈕事件
          const idfButtons = modalBody.querySelectorAll('.idf-list-btn');
          idfButtons.forEach(button => {
            button.addEventListener('click', (e) => {
              const variable = e.target.dataset.variable;
              this.showIDFList(variable);
            });
          });
    
          // 綁定感應器選擇按鈕事件
          const sensorButtons = modalBody.querySelectorAll('.sensor-select-btn');
          sensorButtons.forEach(button => {
            button.addEventListener('click', (e) => {
              const variable = e.target.closest('.form-check').querySelector('.form-check-input').dataset.variable;
              this.showSensorSelection(variable);
            });
          });
    
          // 綁定添加新變量按鈕事件
          const addButton = modalBody.querySelector('.add-variable-btn');
          if (addButton) {
            addButton.addEventListener('click', () => {
              const input = modalBody.querySelector('#newVariableName');
              if (input && input.value) {
                this.addNewVariable(input.value);
              }
            });
          }
        });
    
        console.log('Modal content updated successfully');
    
      } catch (error) {
        console.error('Error updating modal content:', error);
        modalBody.innerHTML = `
          <p class="text-danger">Error updating content: ${error.message}</p>
        `;
      }
    
      // 確保所有選中的變量都有對應的 IDF 設置
      this.cyberVariables.forEach(v => {
        if (!this.selectedIDFs.hasOwnProperty(v)) {
          this.$set(this.selectedIDFs, v, 'IDF List');
        }
      });
    
      console.log('Updated modal content. Current selectedIDFs:', JSON.stringify(this.selectedIDFs));
      
      // 顯示模態框
      $('#cyberVariableModal').modal('show');
    },
  
   
    
    incrementSessionId() {
      if (this.sessionIds.length > 0) {
        const lastSessionId = this.sessionIds[this.sessionIds.length - 1];
        const newSessionId = lastSessionId + 1;
        this.sessionIds.push(newSessionId);
        this.selectedSessionId = newSessionId;
        this.currentSessionId = newSessionId;
      }
    },
    async saveCyberVariables() {
      // 保留原有的狀態顯示代碼
      const statusDiv = document.getElementById('status-messages');
      if (statusDiv) {
        statusDiv.innerHTML = `
          <p class="alert-message">
            <span>Status Information: Waiting for Creating Lecture...</span>
          </p>
        `;
      }
    
      console.log('開始保存 Cyber Variables...');
      localStorage.setItem('isFromCyberSetup', 'true');
      
      const currentLectureId = this.lectureId;
      console.log('Current lecture ID:', currentLectureId);
      
      // 保留原有的實驗描述處理代碼
      const marker = "Create a VPython animation to illustrate the following physics experiment:";
      const index = this.gptPrompt.indexOf(marker);
      if (index !== -1) {
        const mappingMarker = "3. Cyber Input Variable Mapping Information:";
        const mappingIndex = this.gptPrompt.indexOf(mappingMarker);
        
        const experimentText = mappingIndex !== -1 
          ? this.gptPrompt.substring(0, mappingIndex).trim()
          : this.gptPrompt;
        
        const experimentDescription = experimentText.substring(index + marker.length).trim();
        
        localStorage.setItem('experimentText', experimentText);
        localStorage.setItem('experimentDescription', experimentDescription);
      }
    
      let cyberInputMappingInfo = "</br>3. Cyber Input Variable Mapping Information:</br>";
      
      // 修改為支援多個變量的映射生成
      const selectedVariables = this.cyberVariables.filter(v =>
        document.getElementById(v.replace(/\s+/g, '')).checked
      ).map(v => {
        const savedData = this.globalIvList[v] || {};
        const idf = this.selectedIDFs[v] || '';
        let dimensionValues = [];
        
        // 根據不同類型設置維度值
        if (['Acceleration', 'Gyroscope', 'Magnetometer', 'Orientation'].includes(savedData.sensor)) {
          dimensionValues = [savedData.x0 || 0, savedData.x1 || 0, savedData.x2 || 0];
        } else if (savedData.sensor === 'Range Slider') {
          dimensionValues = [savedData.default || 5];
        } else if (['Input Box (Number)', 'Input Box (String)'].includes(savedData.sensor)) {
          dimensionValues = [savedData.default || 0];
        }
        
        const idfName = idf.replace(/Program\d+/, `Program${currentLectureId}`);
        
        // 根據變量類型生成初始值字符串
        const getInitialValue = (values, type, dimensions) => {
          if (dimensions === 1) return `${values[0]}`;
          if (dimensions === 3 && type === 'vector') return `[${values.join(', ')}]`;
          return `[${values.join(', ')}]`;
        };
    
        return {
          name: v,
          idf: idfName,
          sensor: savedData.sensor || '',
          dimensions: savedData.dimensions || 1,
          type: savedData.type || 'value',
          initialValue: getInitialValue(dimensionValues, savedData.type, savedData.dimensions)
        };
      });
    
      // 為每個變量生成映射信息
      selectedVariables.forEach((variable, index) => {
        cyberInputMappingInfo += `\n(${index * 2 + 1}) ${variable.name} is mapped to the variable named ${variable.idf} with an initial value set to a ${variable.dimensions}-dimensional ${variable.type} ${variable.initialValue}</br>`;
        cyberInputMappingInfo += `\n(${index * 2 + 2}) When the value of ${variable.idf} changes, let the animation rerun to the starting point and start with the updated ${variable.name}.</br>\n`;
      });
    
      try {
        const saveMappingInfo = () => new Promise((resolve, reject) => {
          ajaxJson(
            `/edutalk/lecture/${currentLectureId}/save_mapping`,
            'POST',
            {
              cyberInputMappingInfo: cyberInputMappingInfo,
              nextLectureId: parseInt(currentLectureId) + 1
            },
            (data) => resolve(data),
            (jqXHR) => reject(jqXHR)
          );
        });
    
        await saveMappingInfo();
        console.log('映射信息已成功保存到服務器');
        localStorage.setItem('cyberInputMappingInfo', cyberInputMappingInfo);
    
        await this.createLecture();
      } catch (error) {
        console.error('保存失敗:', error);
        if (error.responseJSON?.reason) {
          alert(`保存失敗: ${error.responseJSON.reason}`);
        } else {
          alert('保存失敗,請重試');
        }
        return;
      }
    
      $('#cyberVariableModal').modal('hide');
      this.showSubmitButton = true;
      this.isFirstSubmission = true;
    },
    async fetchSessionIds() {
      const response = await fetch(`/edutalk/lecture/${this.lectureId}/get_sessions`);
      const data = await response.json();
      this.sessionIds = data.sessionIds.sort((a, b) => a - b);
      if (this.sessionIds.length > 0) {
        this.selectedSessionId = this.sessionIds[this.sessionIds.length - 1];
        this.currentSessionId = this.selectedSessionId;  // Update currentSessionId
        this.fetchSerialNumbers();
      }
    },
    updateCurrentSessionId(newSessionId) {
      this.currentSessionId = newSessionId;
    },
    async fetchSerialNumbers() {
      if (!this.selectedSessionId) return;
      try {
        const response = await fetch(`/edutalk/lecture/${this.lectureId}/get_serial_numbers?session_id=${this.selectedSessionId}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        this.serialNumbers = data.serialNumbers.map(item => {
          if (item.mode === 'initial') {
            return { label: `Prompt B ${item.serial_number}`, value: item.serial_number };
          } else if (item.mode === 'fix_error') {
            return { label: `Prompt C ${item.serial_number}`, value: item.serial_number };
          } else if (item.mode === 'modification') {
            return { label: `Prompt D ${item.serial_number}`, value: item.serial_number };
          } else {
            return { label: item.serial_number, value: item.serial_number };
          }
        });
        
        if (this.serialNumbers.length > 0) {
          this.selectedSerialNumber = this.serialNumbers[0].value;  
          await this.fetchLog();  
        } else {
          this.selectedSerialNumber = '';
          this.gptPrompt = '';
          this.updateGeneratedProgram('');
        }
      } catch (error) {
        console.error('Error fetching serial numbers:', error);
        this.serialNumbers = [];
        this.selectedSerialNumber = '';
        this.gptPrompt = '';
        this.updateGeneratedProgram('');
      }
    },
    
    async fetchLog() {
      if (!this.selectedSessionId || !this.selectedSerialNumber) return;
      try {
        const response = await fetch(`/edutalk/lecture/${this.lectureId}/get_log?session_id=${this.selectedSessionId}&serial_number=${this.selectedSerialNumber}`);
        if (!response.ok) {
          if (response.status === 404) {
            console.log('No log found for the selected session and serial number');
            this.gptPrompt = '';
            this.updateGeneratedProgram('');
            return;
          }
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const logData = await response.json();
        
        this.gptPrompt = logData.input || '';  
        this.updateGeneratedProgram(logData.output || '');
        this.currentMode = logData.mode;
        this.isSubmitDisabled = !this.gptPrompt.trim(); 
      } catch (error) {
        console.error('Error fetching log:', error);
        this.gptPrompt = '';
        this.updateGeneratedProgram('');
      }
    },
    toggleMode() {
      this.debugMode = !this.debugMode;
      if (!this.debugMode) {
        this.isLoadingHackMD = true;
        this.gptResponse = null;
        this.fetchHackMDContent();
      } else {
        this.incrementSessionId();
        this.fetchSessionIds();
      }
      // Reset states
      this.isSubmittingToGpt = false;
      this.isFixingError = false;
      this.needRewrite = false;
      this.manualSubmit = false;
    },
    async manualCompileAndRun() {
      if (!this.selectedSessionId || !this.selectedSerialNumber) return;
      const response = await fetch(`/edutalk/lecture/${this.lectureId}/get_log?session_id=${this.selectedSessionId}&serial_number=${this.selectedSerialNumber}`);
      const logData = await response.json();
    
      if (logData.error) {
        console.error(logData.error);
        return;
      }
    
      await this.compileAndRunProgram(logData.output);
    },
    fetchHackMDContent() {
      // Log the URL being fetched
      console.log("Fetching HackMD content from URL:", this.hackmdURL);
  
      if (!this.hackmdURL) {
          this.isLoadingHackMD = false;
          this.gptPrompt = "Error: HackMD URL is missing.";
          return;
      }
  
      this.isLoadingHackMD = true;  // Set loading flag to true
  
      // Construct the API request URL (adjust this based on your backend setup)
      const url = `/edutalk/lecture/${this.lectureId}/hackmd/markdown`;
  
      fetch(url)
          .then(response => {
              // Check if the response is OK (status code 200)
              if (response.ok) {
                  return response.json();
              } else {
                  // If not, throw an error with status and text
                  throw new Error(`Failed to fetch HackMD content. Status: ${response.status} - ${response.statusText}`);
              }
          })
          .then(data => {
              // Handle the response data from the server
              if (data.markdown) {
                  let markdown = data.markdown;
                  console.log('Fetched Markdown:', markdown);
  
                  // Update the GPT prompt with the fetched content
                  this.gptPrompt = markdown;
                  console.log('Updated GPT Prompt:', this.gptPrompt);
              } else if (data.error) {
                  // If the response contains an error field
                  console.error('Error in fetched data:', data.error);
                  this.gptPrompt = `Error: ${data.error}`;
              } else {
                  // Unexpected data format or no markdown content
                  console.error('Unexpected data format:', data);
                  this.gptPrompt = 'Error: Failed to fetch valid HackMD content';
              }
          })
          .catch(error => {
              // Catch any errors that occur during fetch or response processing
              console.error('Error fetching HackMD content:', error);
              this.gptPrompt = `Error: ${error.message}`;
          })
          .finally(() => {
              // Always reset the loading flag after the request is complete
              this.isLoadingHackMD = false;
          });
  },
    
    updateGptPrompt(newPrompt) {
      this.gptPrompt = newPrompt;
    },
    enablePromptInput() {
      const promptTextarea = document.querySelector('textarea[v-model="gptPrompt"]');
      if (promptTextarea) {
        promptTextarea.disabled = false;
      }
    },
    setupErrorHandling() {
      console.group('Error Handler Setup');
      console.log('Adding vpython-error event listener');
      
      try {
        window.addEventListener('vpython-error', this.handleVpythonError);
        console.log('Event listener added successfully');
        
        // 驗證設置
        if (typeof this.handleVpythonError === 'function') {
          console.log('handleVpythonError method verified');
        } else {
          console.error('handleVpythonError is not a function!');
        }
        
      } catch (error) {
        console.error('Failed to setup error handling:', error);
      }
      
      console.groupEnd();
    },

    async handleVpythonError(event) {
      console.group('VPython Error Event Received');
      console.log('Event details:', event.detail);
      console.log('Current fix attempts:', this.fixAttempts);
      console.log('Error timestamp:', event.detail.timestamp);
      
      try {
        const { error, code } = event.detail;
        await this.handleExecutionError(new Error(error), code);
        console.log('Error handled successfully');
      } catch (err) {
        console.error('Failed to handle VPython error:', err);
      }
      
      console.groupEnd();
    },

    async handleExecutionError(error, code) {
      // 忽略CSRF相關錯誤 
      if (error.message && (
        error.message.includes('CSRF') ||
        error.message.includes('token') ||
        error.message.includes('Unknown error')
      )) {
        console.log('Ignoring CSRF/token related error');
        return;
      }
    
      const currentErrorMessage = error.message || 'Unknown error';
      
      // 存储当前轮次的 VPython 代码和错误信息
      if (this.fixAttempts === 0) {
        this.generatedCodes.push(this.vpythonCode);
      }
      this.errorMessages.push(currentErrorMessage);
    
      // 檢查是否達到最大修復次數
      if (this.fixAttempts >= this.maxFixAttempts) {
        const statusDiv = document.getElementById('status-messages');
        if (statusDiv) {
          statusDiv.innerHTML = '<p class="alert-message-error">Status Information: GPT cannot fix errors. Please modify your prompt.</p>';
        }
        // 不再自動顯示 debug modal
        // this.showDebugModal(); // 移除這行
        return;
      }
    
      // 更新状态消息
      const statusDiv = document.getElementById('status-messages');
      if (statusDiv) {
        if (this.fixAttempts === 0) {
          statusDiv.innerHTML = '<p class="alert-message-error">Status Information: The generated code has runtime error.</p>';
        } else {
          statusDiv.innerHTML = `<p class="alert-message-error">Status Information: Waiting for the runtime error to be fixed: Round ${this.fixAttempts + 1}</p>`;
        }
      }
    
      // 開始修復流程
      this.isFixingError = true;
      this.fixAttempts++;
      await this.fixErrorAndResubmit(currentErrorMessage, this.vpythonCode);
    },
    handleGPTError(error, action) {
      // 如果是CSRF錯誤相關,直接返回而不處理
      if (error.reason === 'The CSRF tokens do not match.' ||
          error.message?.includes('CSRF') ||
          error.message?.includes('token') ||
          error.message === 'Unknown error') {
          console.log('Ignoring CSRF/token related error');
          return;
      }
    
      console.error(`Error ${action} the program:`, error);
      this.fixingMessage = `Error occurred while ${action} the program: ${error.message}. Please try again.`;
      this.showErrorMessage(this.fixingMessage);
    },
updateErrorState(state) {
  const statusDiv = document.getElementById('status-messages');
  if (!statusDiv) return;

  const messages = {
    [this.ERROR_STATES.INITIAL_ERROR]: 'Status Information: The generated code has runtime error.',
    [this.ERROR_STATES.FIXING]: `Status Information: Waiting for the runtime error to be fixed: Round ${this.fixAttempts}`,
    [this.ERROR_STATES.MAX_ATTEMPTS]: 'Status Information: GPT cannot fix errors. Please modify your prompt.'
  };

  statusDiv.innerHTML = `<p class="alert-message-error">${messages[state]}</p>`;

  if (state === this.ERROR_STATES.MAX_ATTEMPTS) {
    this.updateGeneratedProgram("# GPT failed to generate your program without errors");
    this.needRewrite = true;
    this.isSubmittingToGpt = false;
    this.isFixingError = false;
  }
},
  
resetErrorState() {
  this.fixAttempts = 0;
  this.isFixingError = false;
  this.needRewrite = false;
  this.fixingMessage = '';
  
  const statusDiv = document.getElementById('status-messages');
  if (statusDiv) {
    statusDiv.innerHTML = '<p class="alert-message">Status Information: GPT returns a program without error</p>';
  }
},

    showSuccessMessage() {
      const statusDiv = document.getElementById('status-messages');
      if (statusDiv) {
        statusDiv.innerHTML = '<p class="alert-message">Status Information: 2.GPT returns a program without error</p>';
      }
    },
    handleSuccessfulExecution(code) {
      this.vpythonCode = code;
      this.updateGeneratedProgram(code);
      this.resetErrorState();
      
      // 成功時顯示狀態訊息
      const statusDiv = document.getElementById('status-messages');
      if (statusDiv) {
        statusDiv.innerHTML = '<p class="alert-message">Status Information: GPT returns a program without error</p>';
      }
    
      if (typeof editor !== 'undefined') {
        editor.setValue(code);
        if (typeof saveCode === 'function') {
          saveCode(() => {
            console.log('Code saved successfully!');
          });
        }
      }
    
      $('#runtime-error').hide();
    
      // 增加這一段強制顯示 preview modal
      // 禁用原本的 QRCode 相關功能
      const originalQRCode = window.QRCode; 
      
      window.QRCode = function(element, options) {
        console.log('QR Code placeholder');
        return {
          clear: function() {},
          makeCode: function() {}
        };
      };
    
      // 顯示模態框
      $('#animation-preview-modal').modal('show');
      
      // 添加必要的模態框背景 
      $('body').addClass('modal-open');
      if(!$('.modal-backdrop').length) {
        $('body').append('<div class="modal-backdrop fade show"></div>');
      }
    
      // 等待模態框完全顯示後再執行其他初始化
      this.$nextTick(() => {
        if(this.token) {
          this.updateRcUrl();
        }
        
        const controlPanel = document.getElementById('control-panel');
        if(controlPanel) {
          controlPanel.src = this.rcUrl;
        }
    
        // 最後再執行動畫程式
        execute(this.vpythonCode);
      });
    
      // 當模態框關閉時恢復原本的 QRCode 
      $('#animation-preview-modal').one('hidden.bs.modal', () => {
        window.QRCode = originalQRCode;
        
        // 清理其他資源
        const rcSlider = document.getElementById('control-slider');
        if (rcSlider) {
          $(rcSlider).rangeslider('destroy');
        }
        if (window.da) {
          window.da.dan.deregister();
          window.da = null;
        }
      });
    },
    async compileAndRunProgram(code) {
      try {
        console.log('Attempting to compile and run VPython code:', code);
        await execute(code);
        console.log('Code executed successfully');
        this.handleSuccessfulExecution(code);
      } catch (error) {
        console.error('Error executing VPython code:', error);
        if (!this.isFixingError) {
          await this.handleExecutionError(error, this.vpythonCode); 
        }
      }
    },
    
     
    toggleDefaultValueInput(varName) {
      const defaultValueInputs = document.querySelectorAll('.default-value-input');
      defaultValueInputs.forEach(input => input.classList.add('d-none'));
    
      const selectedInput = document.getElementById(`default-value-${varName}`);
      if (selectedInput) {
        selectedInput.classList.remove('d-none');
      }
    },
    updateIDFDropdown() {
      const dropdown = document.querySelector('.idf-dropdown');
      if (dropdown) {
          const listContainer = dropdown.querySelector('.idf-list-container ul');
          if (listContainer) {
              listContainer.innerHTML = '';
              
              this.idfVariables.forEach(varName => {
                  const listItem = document.createElement('li');
                  const radio = document.createElement('input');
                  radio.type = 'radio';
                  radio.name = 'idfVariable';
                  radio.value = varName;
                  radio.id = `idf-${varName}`;
                  radio.onchange = () => this.saveIDFSelection(varName);
                  
                  const label = document.createElement('label');
                  label.htmlFor = `idf-${varName}`;
                  label.textContent = varName;
                  
                  listItem.appendChild(radio);
                  listItem.appendChild(label);
                  listContainer.appendChild(listItem);
              });
          }
      }
  },
  addNewIDFVariable(newVariableName, numberOfDimensions) {
    if (!newVariableName || numberOfDimensions < 1 || numberOfDimensions > 9) {
        alert("請輸入有效的變數名稱，並確保維度在 1 到 9 之間。");
        return;
    }

   
    if (numberOfDimensions === 1) {
        this.settingIv.type = 'value';
    } else if (numberOfDimensions === 3) {
        this.settingIv.type = 'array'; 
    } else if (numberOfDimensions === 2 || (numberOfDimensions >= 4 && numberOfDimensions <= 9)) {
        this.settingIv.type = 'array';
    }

    console.log(`新增 IDF 變數: ${newVariableName}, 類型: ${this.settingIv.type}, 維度: ${numberOfDimensions}`);

    
    const newVariable = {
        name: newVariableName,
        type: this.settingIv.type,
        dim: numberOfDimensions,
        default: new Array(numberOfDimensions).fill(0) 
    };

    
    if (!this.idfVariables.includes(newVariableName)) {
        this.idfVariables.push(newVariableName);
    }

    
    this.$set(this.selectedIDFs, newVariableName, newVariableName);

    
    this.selectedIDF = {
        name: newVariableName,
        dimensions: numberOfDimensions,
        type: this.settingIv.type
    };

    
    this.updateIDFDropdown(); 

    
    this.$nextTick(() => {
        this.$forceUpdate();
    });

    
    $('#addNewVariableModal').modal('hide');
    $('#addDimensionModal').modal('hide');

   
    this.showIDFList(newVariableName);

    const idfButton = document.querySelector(`#buttons-${newVariableName.replace(/\s+/g, '')} button:first-child`);
    if (idfButton) {
        idfButton.textContent = newVariableName;
    }
},
    renderIDFVariables() {
      const idfContainer = document.getElementById('idf-list-container');
      if (!idfContainer) return;
  
      idfContainer.innerHTML = '';
  
      this.cyberVariables.forEach(variable => {
        const div = document.createElement('div');
        div.className = 'idf-variable';
        div.textContent = `${variable.name} (${variable.type}, ${variable.dimensions}D)`;
  
        idfContainer.appendChild(div);
      });
    },
    
    showDimensionPrompt(newVarName) {
      // Here you could integrate a custom modal instead of a simple prompt
      const dimension = parseInt(prompt("Please enter the number of parameters (dimensions):", "1"));
      if (dimension >= 1 && dimension <= 9) {
        this.addNewIDFVariable(newVarName, dimension);
      } else {
        alert("Please enter a valid number between 1 and 9.");
      }
    },
    showAddNewVariableDimensionsDialog(newVarName) {
      // Show a modal or just prompt to get the dimensions
      // As per your requirement, we will use a simple spinner for this example
      this.numberOfDimensions = 1; // default value set to 1
      this.showDimensionPrompt(newVarName);
    },
    showAddNewVariableDialog() {
      this.newVariableName = ''; // Reset the new variable name
      $('#addNewVariableModal').modal('show');
    },
    showDimensionPrompt() {
      $('#addNewVariableModal').modal('hide'); // Hide the name input modal
      $('#addDimensionModal').modal('show'); // Show the dimension input modal
    },
    renderIDFVariables() {
      const idfContainer = document.getElementById('idf-container');
      if (!idfContainer) return;
  
      idfContainer.innerHTML = '';
  
      this.idfVariables.forEach(varName => {
          const div = document.createElement('div');
          div.className = 'form-check d-flex align-items-center mb-2';
  
          const radio = document.createElement('input');
          radio.className = 'form-check-input';
          radio.type = 'radio';
          radio.name = 'idfVariable';
          radio.id = varName;
          radio.value = varName;
          radio.onclick = () => {
              this.toggleDefaultValueInput(varName);
          };
  
          const label = document.createElement('label');
          label.className = 'form-check-label mr-2';
          label.htmlFor = varName;
          label.textContent = varName;
  
          const defaultValueDiv = document.createElement('div');
          defaultValueDiv.className = 'default-value-input d-none';
          defaultValueDiv.id = `default-value-${varName}`;
  
          const defaultValueLabel = document.createElement('label');
          defaultValueLabel.className = 'mr-2';
          defaultValueLabel.textContent = 'Default Value:';
  
          const defaultValueInput = document.createElement('input');
          defaultValueInput.type = 'text';
          defaultValueInput.className = 'form-control form-control-sm';
  
          defaultValueDiv.appendChild(defaultValueLabel);
          defaultValueDiv.appendChild(defaultValueInput);
  
          div.appendChild(radio);
          div.appendChild(label);
          div.appendChild(defaultValueDiv);
          idfContainer.appendChild(div);
      });
  },
  showIDFList(variable) {
    console.log(`顯示 ${variable} 的 IDF 列表`);
    this.currentVariable = variable;

   
    const dropdown = document.createElement('div');
    dropdown.className = 'idf-dropdown';

   
    const addNewLink = document.createElement('a');
    addNewLink.href = '#';
    addNewLink.textContent = 'add new';
    addNewLink.className = 'add-new-variable';
    addNewLink.onclick = (e) => {
        e.preventDefault();
        this.showAddNewVariableDialog();
    };
    dropdown.appendChild(addNewLink);

   
    const idfListContainer = document.createElement('div');
    idfListContainer.className = 'idf-list-container';

   
    const idfList = document.createElement('ul');
    this.idfVariables.forEach(varName => {
        const listItem = document.createElement('li');
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'idfVariable';
        radio.value = varName;
        radio.id = `idf-${varName}`;
        radio.onchange = () => this.saveIDFSelection(varName);

        const label = document.createElement('label');
        label.htmlFor = `idf-${varName}`;
        label.textContent = varName;

        listItem.appendChild(radio);
        listItem.appendChild(label);
        idfList.appendChild(listItem);
    });
    idfListContainer.appendChild(idfList);
    dropdown.appendChild(idfListContainer);

    
    const idfButton = document.getElementById(`idf-btn-${this.currentVariable.replace(/\s+/g, '')}`);
    if (idfButton) {
        idfButton.parentNode.insertBefore(dropdown, idfButton.nextSibling);
    } else {
        console.error(`IDF button not found for ${this.currentVariable}`);
    }
},
    closeIDFModal() {
      console.log('Closing IDF modal...'); 
      this.showIDFModal = false;
      $('#idfListModal').modal('hide');
      console.log('IDF modal closed'); 
    },
    getIDFInfo(variable) {
      const idfInfo = {
          name: variable,
          dimensions: 1,
          type: 'value'
      };
  
      if (['Gyroscope_I', 'Magnetometer_I', 'Orientation_I', 'Velocity_I'].includes(variable)) {
          idfInfo.dimensions = 3;
          idfInfo.type = 'array';
      }
      
     
      if (this.newVariableName && this.newVariableName === variable) {
          idfInfo.dimensions = this.numberOfDimensions;
          idfInfo.type = this.settingIv.type; 
      }
  
      return idfInfo;
  },
  showSensorSelection(variable) {
    console.log(`顯示感應器選擇模態框，變數: ${variable}`);
    
    this.currentVariable = variable; // 保存當前變量名稱
    const selectedIDF = this.selectedIDFs[variable]; // 獲取已選擇的 IDF
    
    // 使用選定的 IDF 名稱而不是原始變量名稱
    this.selectedIDF = {
      name: selectedIDF || variable, // 優先使用選定的 IDF 名稱
      dimensions: 1,
      type: 'value',
      selectedIDF: selectedIDF // 保存選中的 IDF 用於其他功能
    };

    // 根據選中的 IDF 設置特定屬性
    if (['Gyroscope_I', 'Magnetometer_I', 'Orientation_I', 'Acceleration_I'].includes(selectedIDF)) {
      this.selectedIDF.dimensions = 3;
      this.selectedIDF.type = 'vector';
    } else if (selectedIDF === this.newVariableName) {
      this.selectedIDF.dimensions = this.numberOfDimensions;
      this.selectedIDF.type = this.settingIv.type;
    }

    console.log(`選擇的 IDF 詳情: ${JSON.stringify(this.selectedIDF)}`);

    // 初始化參數保持不變
    if (this.selectedIDF.type === 'vector' && this.selectedIDF.dimensions === 3) {
      this.settingIv.params = [{
        mac_addr: 'smartphone_mac_address',
        sensor: 'Gyroscope',
        model: 'Smartphone',
        device: 'Smartphone Device',
        x0: '0',
        x1: '0',
        x2: '0',
        index: 0
      }];
    } else {
      this.settingIv.params = Array.from({length: this.selectedIDF.dimensions}, (_, i) => ({
        mac_addr: 'smartphone_mac_address',
        sensor: 'Range Slider',
        model: 'Smartphone',
        device: 'Smartphone Device',
        min: 0,
        max: 10,
        default: 5,
        x0: '0',
        x1: '0',
        x2: '0',
        index: i
      }));
    }

    this.$nextTick(() => {
      // 更新模態框標題以顯示IDF名稱
      const modalTitle = document.querySelector('#physicalFeatureBindingModal .modal-title');
      if(modalTitle) {
        modalTitle.textContent = `Physical Feature Binding for ${this.selectedIDF.name}`;
      }
      
      const dimensionsLabel = document.getElementById('dimensions-label');
      const typeLabel = document.getElementById('type-label');

      if (dimensionsLabel) {
        dimensionsLabel.textContent = `Number of parameters (dimensions): ${this.selectedIDF.dimensions}`;
      }

      if (typeLabel) {
        typeLabel.textContent = `Type of variable: ${this.selectedIDF.type}`;
      }

      this.updateSensors(0);
      
      $('#physicalFeatureBindingModal').modal('show');
    });
},
  updateSensors(index) {
    const param = this.settingIv.params[index];
    const selectedDevice = this.availableSensorDevices.find(d => d.mac_addr === param.mac_addr);
    if (selectedDevice) {
      param.model = selectedDevice.model;
      param.device = selectedDevice.model;
  
      // Update sensorOptions for Smartphone
      if (selectedDevice.model === 'Smartphone') {
        this.sensorOptions['Smartphone'] = {
          'Acceleration': {},
          'Gyroscope': {},
          'Magnetometer': {},
          'Orientation': {},
          'Range Slider': {},
          'Input Box (Number)': {},
          'Input Box (String)': {},
          'Alcohol(Morsensor)': {},
          'Humidity(Morsensor)': {},
          'UV(Morsensor)': {}
        };
      }
    }
    this.initParam(index);
  },
  savePhysicalFeatureBinding() {
    let dimensionValues = this.settingIv.params.map(param => {
        if (['Acceleration', 'Gyroscope', 'Magnetometer', 'Orientation'].includes(param.sensor)) {
            return `[${param.x0}, ${param.x1}, ${param.x2}]`;
        } else if (param.sensor === 'Range Slider') {
            return param.default;
        } else if (['Input Box (Number)', 'Input Box (String)'].includes(param.sensor)) {
            return param.default;
        }
    });

    let initialValue = '';
    if (this.selectedIDF.dimensions === 1) {
        initialValue = `${dimensionValues[0]}`;
    } else if (this.selectedIDF.dimensions === 3 && this.selectedIDF.type === 'vector') {
        initialValue = `[${dimensionValues.join(', ')}]`;
    } else {
        initialValue = `[${dimensionValues.join(', ')}]`;
    }

    const cyberInputMappingInfo = `\n\n3. Cyber Input Variable Mapping Information:
    (1) ${this.currentVariable} is mapped to the variable named ${this.selectedIDF.name} with an initial value set to a ${this.selectedIDF.dimensions}-dimensional ${this.selectedIDF.type} ${initialValue}
    (2) When the value of ${this.selectedIDF.name} changes, let the animation rerun to the starting point and start with the updated ${this.currentVariable}.
    `;

    this.gptPrompt += cyberInputMappingInfo;

    this.$nextTick(() => {
        const sensorButton = document.querySelector(`#buttons-${this.currentVariable.replace(/\s+/g, '')} .sensor-select-btn`);
        if (sensorButton && this.settingIv.params[0] && this.settingIv.params[0].sensor) {
            sensorButton.textContent = this.settingIv.params[0].sensor;
            console.log(`Updated Sensor Selection button text to: ${this.settingIv.params[0].sensor}`);
        } else {
            console.log('Failed to update Sensor Selection button text');
        }
    });

    $('#physicalFeatureBindingModal').modal('hide');
    this.showSubmitButton = true;
    this.isFirstSubmission = true;  // Reset the first submission flag

   
    let ivData = {
        sensor: this.settingIv.params[0].sensor,
        device: this.settingIv.params[0].device,
        ...this.settingIv.params[0]
    };

   
    if (this.settingIv.params.length > 1) {
        this.settingIv.params.forEach((param, index) => {
            ivData[`param${index + 1}`] = param;
        });
    }

  
    this.$set(this.globalIvList, this.currentVariable, ivData);

    console.log(`Saved variable ${this.currentVariable} with settings:`, this.globalIvList[this.currentVariable]);
},
availableSensors(model) {
  if (model === 'Smartphone') {
    return [
      'Acceleration',
      'Gyroscope',
      'Magnetometer',
      'Orientation',
      'Range Slider',
      'Input Box (Number)',
      'Input Box (String)',
      'Alcohol(Morsensor)',
      'Humidity(Morsensor)',
      'UV(Morsensor)'
    ];
  }
  return Object.keys(this.sensorOptions[model] || {});
},
  
    initParam(index) {
      const param = this.settingIv.params[index];
      
   
      if (param.device && param.device in this.sensorOptions && param.sensor in this.sensorOptions[param.device]) {
          const sensorOption = this.sensorOptions[param.device][param.sensor];
          if (sensorOption) {
              param.sensor_unit = sensorOption.unit || 'None';
              param.type = sensorOption.type || 'float';
          }
   
          if (['Acceleration', 'Gyroscope', 'Magnetometer', 'Orientation'].includes(param.sensor)) {
              param.x0 = param.x0 || '0';
              param.x1 = param.x1 || '0';
              param.x2 = param.x2 || '0';
          } else if (param.sensor === 'Range Slider') {
              param.min = param.min || '0';
              param.max = param.max || '10';
              param.default = param.default || '5';
          } else if (['Input Box (Number)', 'Input Box (String)'].includes(param.sensor)) {
              param.default = param.default || '';
          }
      } else {
          console.error(`Sensor option not found for device: ${param.device}, sensor: ${param.sensor}`);
      }
      
   
      this.$forceUpdate(); 
  },
    selectDfIv() {
      const selectedIv = this.ivList.find(iv => iv.giv_name === this.settingIv.giv_name);
      if (selectedIv) {
        this.settingIv = {
          show: true,
          giv_name: selectedIv.giv_name,
          type: selectedIv.type,
          params: JSON.parse(JSON.stringify(selectedIv.params))
        };
      }
    },
    closeSensorModal() {
      this.showSensorModal = false;
    },
    
    selectIDF(idf) {
    
      console.log(`Selected IDF for ${this.currentVariable}: ${idf}`);
      this.closeIDFModal();
    },
    
    selectSensor(sensor) {
 
      console.log(`Selected sensor for ${this.currentVariable}: ${sensor}`);
      this.closeSensorModal();
    },
    toggleButtons(variable) {
      console.log(`Toggling buttons for ${variable}`);
      const checkbox = document.getElementById(variable.replace(/\s+/g, ''));
      const buttons = document.getElementById(`buttons-${variable.replace(/\s+/g, '')}`);
      if (checkbox && buttons) {
          buttons.style.display = checkbox.checked ? 'inline-block' : 'none';
      }
      if (checkbox.checked) {
          console.log(`Variable ${variable} is selected`);
      } else {
          console.log(`Variable ${variable} is deselected`);
      }
  },
  
  
  addCheckboxListeners() {
    this.cyberVariables.forEach(v => {
      const checkbox = document.getElementById(v.replace(/\s+/g, ''));
      if (checkbox) {
        checkbox.addEventListener('change', () => this.toggleButtons(v));
      }
    });
  },
  
  addIDFButtonListeners() {
    this.cyberVariables.forEach(v => {
      const idfButton = document.getElementById(`idf-btn-${v.replace(/\s+/g, '')}`);
      if (idfButton) {
        idfButton.addEventListener('click', () => this.showIDFList(v));
      }
    });
  },
  
  addSensorButtonListeners() {
    this.cyberVariables.forEach(v => {
      const sensorButton = document.querySelector(`#buttons-${v.replace(/\s+/g, '')} .sensor-select-btn`);
      if (sensorButton) {
        sensorButton.addEventListener('click', () => this.showSensorSelection(v));
      }
    });
  },
  
  addNewVariableListener() {
    const addButton = document.querySelector('.input-group-append button');
    if (addButton) {
      addButton.addEventListener('click', () => this.addNewVariable());
    }
  },
    addCheckboxListeners() {
      this.cyberVariables.forEach(v => {
        const checkbox = document.getElementById(v.replace(/\s+/g, ''));
        if (checkbox) {
          checkbox.addEventListener('change', () => this.toggleButtons(v));
        }
      });
    },
  
    hideCyberVariableModal() {
      const modal = document.getElementById('cyberVariableModal');
      modal.setAttribute('inert', 'true');
      modal.setAttribute('aria-hidden', 'true');
      $('#cyberVariableModal').modal('hide');
    },
  
  
    triggerAutoRedirect() {
      if (!this.isFixingError) {
       
        this.gptResponse = true;
        
       
        const statusDiv = document.getElementById('status-messages');
        if (statusDiv) {
          statusDiv.innerHTML = '<p class="alert-message">Status Information: 4.GPT returns a program without error</p>';
        }
      }
      
   
      this.needRewrite = false;
    
      
      if (!this.isFixingError && !this.needRewrite) {
        console.log('Showing animation preview modal');
        
        if (this.vpythonCode) {
          try {
         
            if (typeof updateCodeMirror === 'function') {
              updateCodeMirror(this.vpythonCode);
            }
            
           
            if (typeof saveCode === 'function') {
              saveCode(() => {
                console.log('Code saved');
             
                this.showAnimationPreview();
              }, false);
            }
          } catch (error) {
            console.error('Error preparing preview:', error);
          }
        }
      }
    },

    async fixErrorAndResubmit(errorMessage, code) {
      if (this.fixAttempts > this.maxFixAttempts) {
        this.updateGeneratedProgram("# GPT failed to generate your program without errors");
        this.needRewrite = true;
        this.isSubmittingToGpt = false;
        this.isFixingError = false;
        return;
      }
    
      const fixPrompt = `Please fix the following error in the program:\n${errorMessage}\n\nHere's the current program:\n${code}`;
      
      try {
        const response = await fetch(`/edutalk/lecture/${this.lectureId}/submit_to_gpt`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': this.csrfToken
          },
          body: JSON.stringify({
            prompt: fixPrompt,
            mode: 'fix_error' 
          })
        });
    
        const data = await response.json();
        
        if (data.program) {
          // 存储修复后的 VPython 代码
          this.generatedCodes.push(data.program);
          
          this.vpythonCode = data.program;
          this.updateGeneratedProgram(data.program);
          await this.saveGptInteraction(fixPrompt, data.program, 'fix_error');
          
          this.isFixingError = false;
          await this.compileAndRunProgram(data.program);
        }
      } catch (error) {
        console.error('Error:', error);
        this.handleGPTError(error, 'fixing');
      }
    },
    extractErrorMessage(errorText) {
      return errorText;
    },
    submitToGpt() {
      this.manualSubmit = true;
      
      if (this.fixAttempts >= this.maxFixAttempts) {
        this.showDebugModal();
        return;
      }
    
      // 根據是否已有程式碼來判斷是初始提交還是修改
      if (this.vpythonCode) {
        this.isProcessingModification = true;
        this.submitToGptWithModification();
      } else {
        this.isProcessingModification = false; 
        this.submitInitialToGpt();
      }
    },
    
  
async submitInitialToGpt() {
  try {
    this.manualSubmit = true;
    this.isSubmittingToGpt = true;
    this.isFixingError = false;
    this.needRewrite = false;
    this.gptResponse = null;
    this.fixAttempts = 0;

    const statusDiv = document.getElementById('status-messages');
    if (statusDiv) {
      statusDiv.innerHTML = `
        <p class="alert-message">
          <span>Status Information: Waiting for GPT to generate program</span>
        </p>
      `;
    }

    // 獲取 CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
      throw new Error('CSRF token not found');
    }

    let cleanedPrompt = this.gptPrompt.replace(/```python/g, '').replace(/```/g, '').trim();

    const response = await fetch(`/edutalk/lecture/${this.lectureId}/submit_to_gpt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({
        prompt: cleanedPrompt,
        mode: 'initial'
      }),
      credentials: 'include'
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.reason || 'API request failed');
    }

    const data = await response.json();

    if (data.program) {
      
      this.vpythonCode = data.program;
      this.updateGeneratedProgram(data.program);

      try {
        await this.saveGptInteraction(cleanedPrompt, data.program, 'initial');
        await this.compileAndRunProgram(data.program);

        if (statusDiv && !this.isFixingError) {
          statusDiv.innerHTML = '<p class="alert-message">Status Information: GPT returns a program without error</p>';
          
          setTimeout(() => {
            $('#animation-preview-modal').modal('show');
            $('body').addClass('modal-open');
            if (!$('.modal-backdrop').length) {
              $('body').append('<div class="modal-backdrop fade show"></div>');
            }
          }, 500);
        }
      } catch (error) {
        console.error('Error in execution:', error);
        await this.handleExecutionError(error, data.program);
      }
    }

  } catch (error) {
    console.error('Error:', error);
    this.handleGPTError(error, 'generating');
    if (statusDiv) {
      statusDiv.innerHTML = `<p class="alert-message-error">Error: ${error.message}</p>`;
    }
  } finally {
    this.isSubmittingToGpt = false;
    this.manualSubmit = false;
  }
},

// 新增輔助函數
async initializePreviewPanel() {
  if (this.token) {
    this.updateRcUrl();
    
    const controlPanel = document.getElementById('control-panel');
    if (controlPanel) {
      controlPanel.src = this.rcUrl;
      
      // 等待控制面板載入完成
      await new Promise((resolve) => {
        controlPanel.onload = resolve;
      });
    }
  } else {
    // 如果沒有 token，嘗試獲取新的
    const token = await this.getNewToken();
    if (token) {
      this.token = token;
      await this.initializePreviewPanel();
    }
  }
},
    showStatusMessage(message, showSpinner = true) {
      const statusDiv = document.getElementById('status-messages');
      if (statusDiv) {
        statusDiv.innerHTML = `
          <p class="alert-message">
            <span>${message}</span>

          </p>
        `;
      }
    },
    
  async sendRequestToGPT(url, requestBody) {
    console.log('Sending request to:', url);
    console.log('Request body:', JSON.stringify(requestBody, null, 2));

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': this.csrfToken
        },
        body: JSON.stringify(requestBody),
        credentials: 'include'
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    return await response.json();
},



handleGPTError(error, action) {
  // 忽略所有錯誤,直接繼續執行
  console.log('Ignored GPT error:', error);
  
  // 更新狀態訊息但不顯示錯誤
  const statusDiv = document.getElementById('status-messages');
  if (statusDiv) {
    statusDiv.innerHTML = `
      <p class="alert-message">
        <span>Status Information: Processing request...</span>
      </p>
    `;
  }
  
  // 重置狀態
  this.isFixingError = false;
  this.needRewrite = false;
  this.isSubmittingToGpt = false;
}

,showDebugModal() {
  const debugModal = document.createElement('div');
  debugModal.id = 'debug-error-modal';
  
  const modalContent = document.createElement('div');
  modalContent.className = 'modal-content';
  modalContent.innerHTML = `
    <div class="modal-header">
      <h5 class="modal-title">Debug</h5>
      <button class="close-button" onclick="document.getElementById('debug-error-modal').remove()">×</button>
    </div>
    <div class="modal-body" style="max-height: 400px; overflow-y: auto;">
      ${Array(this.fixAttempts).fill().map((_, i) => `
        <div style="margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 500;">Round ${i + 1}:</span>
            <button class="btn btn-primary" 
                    onclick="animationCreateApp.showGeneratedCode(${i + 1})"
                    style="font-size: 14px;">
              Generated Code with Error
            </button>
          </div>
          <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; margin-top: 8px;">
            Error Message: ${this.errorMessages[i] || 'Unknown error'}
          </div>
        </div>
      `).join('')}
    </div>
  `;

  debugModal.appendChild(modalContent);
  document.body.appendChild(debugModal);

  debugModal.addEventListener('click', (e) => {
    if (e.target === debugModal) {
      debugModal.remove();
    }
  });
},
saveGptInteraction(input, output, mode) {
  const interaction = {
    mode: mode,
    input: input,
    output: output
  };

  // 忽略錯誤直接執行
  fetch(`/edutalk/lecture/${this.lectureId}/save_gpt_interaction`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(interaction),
    credentials: 'include'
  })
  .then(response => response.json())
  .then(data => {
    console.log("Save interaction response:", data);
    if (data.new_session_id) {
      this.updateCurrentSessionId(data.new_session_id);
    }
    if (data.new_serial_number) {
      this.fetchSerialNumbers();
    }
  })
  .catch(error => {
    // 忽略錯誤
    console.log("Ignored error saving interaction:", error);
  });
},
      async checkNextLogEntry() {
        if (!this.selectedSessionId || !this.selectedSerialNumber) return false;
        
        const currentIndex = this.serialNumbers.findIndex(item => item.value == this.selectedSerialNumber);
        if (currentIndex === -1 || currentIndex === this.serialNumbers.length - 1) return false;
        
        const nextSerialNumber = this.serialNumbers[currentIndex + 1].value;
        const response = await fetch(`/edutalk/lecture/${this.lectureId}/get_log?session_id=${this.selectedSessionId}&serial_number=${nextSerialNumber}`);
        const nextLogData = await response.json();
        
        return nextLogData.mode === 'fix_error';
      },      
      async submitToGptWithModification() {
        try {
          this.isSubmittingToGpt = true;
          this.isFixingError = false;
          this.needRewrite = false;
          this.gptResponse = null;
          this.fixAttempts = 0;
      
          const statusDiv = document.getElementById('status-messages');
          if (statusDiv) {
            statusDiv.innerHTML = `
              <p class="alert-message">
                <span>Status Information: Waiting for GPT to modify program</span>
              </p>
            `;
          }
      
          // 構建修改提示
          const modificationPrompt = `Please modify the following program based on this instruction:\n${this.gptPrompt}\n\nCurrent program:\n${this.vpythonCode}`;
      
          const response = await fetch(`/edutalk/lecture/${this.lectureId}/submit_to_gpt`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': this.csrfToken
            },
            body: JSON.stringify({
              prompt: modificationPrompt,
              mode: 'modification'
            })
          });
      
          const data = await response.json();
      
          if (data.program) {
            this.vpythonCode = data.program;
            //this.needsSceneRefresh = true; // 標記需要刷新
            this.updateGeneratedProgram(data.program);
            await this.saveGptInteraction(modificationPrompt, data.program, 'modification');
            await this.compileAndRunProgram(data.program);
      
            if (statusDiv && !this.isFixingError) {
              statusDiv.innerHTML = '<p class="alert-message">Status Information: Program modified successfully</p>';
            }
          }
        } catch (error) {
          console.error('Error in modification:', error);
          this.handleGPTError(error, 'modifying');
        } finally {
          this.isSubmittingToGpt = false;
          this.isProcessingModification = false;
        }
      }
    ,
    onPreviewModalClose() {
      // 當動畫預覽 modal 關閉時，重置修改狀態
      this.isPromptModified = false;
  },

  onPromptChange() {
    if (this.vpythonCode) {
      this.isProcessingModification = true;
    }
  },
     
      
      extractPythonCode(responseText) {
        const codeBlockRegex = /```python([\s\S]*?)```/;
        const match = responseText.match(codeBlockRegex);
        if (match) {
          return match[1].trim();  // Return only the code between the code blocks
        }
        return responseText; // Return the full text if no code blocks are found
      },
      async handleGPTResponse(data, requestBody) {
        if (data.program && data.program.trim().length > 0) {
          try {
            await this.saveGptInteraction(requestBody.prompt, data.program, requestBody.mode);
            
            
            this.vpythonCode = data.program;
            this.gptResponse = data;
            
           
            const generatedProgramTextarea = document.getElementById('generated-program');
            if (generatedProgramTextarea) {
              generatedProgramTextarea.value = data.program;
              if (this.vpythonEditor) {
                this.vpythonEditor.setValue(data.program);
                this.vpythonEditor.refresh();
              }
            }
      
           
            await this.compileAndRunProgram(data.program);
      
          } catch (error) {
            console.error('Error in handleGPTResponse:', error);
            throw error;
          }
        } else {
          throw new Error("Received empty or invalid program from GPT");
        }
      },
      
async getAnimationContent() {
  try {
    
    const response = await fetch('/animation.html');
    let content = await response.text();

   
    content = content.replace('id="canvas"', 'id="preview-canvas"');
    
    return content;

  } catch (error) {
    console.error('Error getting animation content:', error);
    return '<div>Error loading animation preview</div>';
  }
},


initializePreviewAnimation() {
  if(this.vpythonCode) {
    try {
      
      const canvas = document.getElementById('preview-canvas');
      if(canvas) {
        canvas.width = 700;
        canvas.height = 400;
      }

      
      if(typeof execute === 'function') {
        execute(this.vpythonCode);
      }

      
      this.bindPreviewControls();

    } catch(error) {
      console.error('Error initializing preview:', error);
    }
  }
},


bindPreviewControls() {
  const runBtn = document.getElementById('preview-run');
  const pauseBtn = document.getElementById('preview-pause');
  const resetBtn = document.getElementById('preview-reset');

  if(runBtn) runBtn.onclick = () => this.runPreview();
  if(pauseBtn) pauseBtn.onclick = () => this.pausePreview();
  if(resetBtn) resetBtn.onclick = () => this.resetPreview();
},


runPreview() {
  if(typeof play === 'function') play();
},

pausePreview() {
  if(typeof pause === 'function') pause(); 
},

resetPreview() {
  if(this.vpythonCode) {
    execute(this.vpythonCode);
  }
},
showAnimationPreview() {
  if (!this.isFixingError) {
    $('#animation-preview-modal').modal('show');
    
    // Clean existing elements
    const existingCanvas = document.querySelectorAll('#animation-preview-modal canvas:not(#qrcode)');
    existingCanvas.forEach(canvas => canvas.remove());
    const existingHandles = document.querySelectorAll('.ui-resizable-handle');
    existingHandles.forEach(handle => handle.remove());

    $('#animation-preview-modal').modal({
      backdrop: 'static',
      keyboard: false,
      show: true
    });

    $('body').addClass('modal-open');
    if(!$('.modal-backdrop').length) {
      $('body').append('<div class="modal-backdrop fade show"></div>');
    }

    this.$nextTick(() => {
      if(this.token) {
        this.updateRcUrl();
      }
      
      const controlPanel = document.getElementById('control-panel');
      if(controlPanel) {
        controlPanel.src = this.rcUrl;
      }

      // Handle permission modal clicks
      const simulateMultipleClicks = () => {
        const modal = controlPanel.contentDocument.getElementById('permission_modal');
        if (modal) {
          Array(5).fill().forEach((_, index) => {
            setTimeout(() => {
              try {
                const clickEvent = new MouseEvent('click', {
                  view: controlPanel.contentWindow,
                  bubbles: true,
                  cancelable: true,
                  clientX: modal.getBoundingClientRect().left + 10,
                  clientY: modal.getBoundingClientRect().top + 10,
                  screenX: modal.getBoundingClientRect().left + 10,
                  screenY: modal.getBoundingClientRect().top + 10
                });
                modal.dispatchEvent(clickEvent);
                if($(modal).is(':visible')) {
                  $(modal).trigger('click');
                }
              } catch(error) {
                console.error(`Click ${index + 1} failed:`, error);
              }
            }, 200 * (index + 1));
          });
        }
      };

      const checkAndClick = setInterval(() => {
        try {
          const modal = controlPanel.contentDocument.getElementById('permission_modal');
          if (modal && $(modal).is(':visible')) {
            simulateMultipleClicks();
            clearInterval(checkAndClick);
          }
        } catch(error) {
          console.error('Modal check error:', error);
        }
      }, 100);

      setTimeout(() => clearInterval(checkAndClick), 5000);
    });

    if (this.vpythonCode) {
      const deviceFrame = document.getElementById('device-iframe');
      if (deviceFrame) {
        const baseUrl = 'https://emily.iottalk.tw';
        const encodedCode = encodeURIComponent(this.vpythonCode);
        deviceFrame.src = `${baseUrl}/edutalk/lecture/${this.lectureId}/vp?code=${encodedCode}`;
        
        deviceFrame.onload = () => {
          if (deviceFrame.contentWindow) {
            deviceFrame.contentWindow.postMessage({
              type: 'execute',
              code: this.vpythonCode
            }, '*');
          }
        };
      }
    }

    // Initialize RC slider and handle cleanup
    this.initializeRCSlider();
  }
},

initializeRCSlider() {
  this.getNewToken().then(token => {
    if(!token) return;

    const rcSlider = document.getElementById('control-slider');
    if(!rcSlider) return;

    this.setupRCSlider(rcSlider, token);
    this.setupQRCode(token);
  }).catch(console.error);
},

setupRCSlider(rcSlider, token) {
  const selectedIDF = Object.entries(this.selectedIDFs).find(([_, value]) => value !== 'IDF List');
  if (!selectedIDF) return;

  const [variableName, idfName] = selectedIDF;
  rcSlider.setAttribute('name', idfName);

  $(rcSlider).rangeslider({
    polyfill: false,
    onInit: function() {
      this.output = $('<output class="column has-text-centered">').insertAfter(this.$range).html(this.$element.val());
    },
    onSlide: function(position, value) {
      this.output.html(value);
    },
    onSlideEnd: this.handleSliderChange.bind(this, idfName, variableName)
  });
}
,
handleSliderChange(idfName, variableName, position, value) {
  const numValue = parseFloat(value);
  const dateTime = new Date().getTime();

  if (!window.da) {
    this.initializeDA(idfName, value);
  }

  if (window.da) {
    window.da.push(idfName, [numValue, dateTime, idfName]);
  }

  const deviceFrame = document.getElementById('device-iframe');
  if (deviceFrame?.contentWindow) {
    deviceFrame.contentWindow.postMessage({
      type: 'updateVariable',
      name: idfName,
      originalName: variableName,
      value: numValue
    }, '*');
  }
},
initPreviewEnvironment() {
  const previewCanvas = document.getElementById('preview-canvas');
  const glowscriptDiv = document.getElementById('glowscript');
  
  // 設置Canvas大小
  previewCanvas.width = 700;
  previewCanvas.height = 400;
  
  // 綁定控制按鈕事件
  document.getElementById('preview-run').onclick = () => this.runPreviewAnimation();
  document.getElementById('preview-pause').onclick = () => this.pausePreviewAnimation();
  document.getElementById('preview-reset').onclick = () => this.resetPreviewAnimation();
},

// 設置變量面板
setupVariablePanel() {
  const variablePanel = document.getElementById('variable-panel');
  variablePanel.innerHTML = '';
  
  // 從代碼中解析出所有變量
  const variables = this.parseVariablesFromCode(this.vpythonCode);
  
  // 為每個變量創建控制元件
  variables.forEach(variable => {
    const control = this.createVariableControl(variable);
    variablePanel.appendChild(control);
  });
},

// 解析代碼中的變量
parseVariablesFromCode(code) {
  const variables = [];
  // 使用正則表達式找出所有變量定義
  const varRegex = /(\w+)_[IO]\s*=/g;
  let match;
  while ((match = varRegex.exec(code)) !== null) {
    variables.push({
      name: match[1],
      type: match[0].endsWith('_I=') ? 'input' : 'output'
    });
  }
  return variables;
},

// 創建變量控制元件
createVariableControl(variable) {
  const div = document.createElement('div');
  div.className = 'variable-control';
  
  const label = document.createElement('label');
  label.textContent = variable.name;
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'form-control';
  input.value = '0';
  input.onchange = (e) => this.updateVariable(variable.name, e.target.value);
  
  div.appendChild(label);
  div.appendChild(input);
  return div;
},

// 運行預覽動畫
async runPreviewAnimation() {
  try {
    // 使用VPython運行動畫代碼
    if (typeof execute === 'function') {
      await execute(this.vpythonCode);
    }
  } catch (error) {
    console.error('Error running preview animation:', error);
  }
},

// 暫停預覽動畫
pausePreviewAnimation() {
  // 實現暫停功能
  if (typeof pause === 'function') {
    pause();
  }
},

// 重置預覽動畫
resetPreviewAnimation() {
  // 實現重置功能
  this.runPreviewAnimation();
},

// 更新變量值
updateVariable(name, value) {
  // 實現變量更新邏輯
  if (typeof updateVariable === 'function') {
    updateVariable(name, value);
  }
},
    showErrorMessage(message) {
      const errorMessageElement = document.getElementById('error-message');
      if (errorMessageElement) {
        errorMessageElement.textContent = message;
        errorMessageElement.style.display = 'block';

        setTimeout(() => {
          errorMessageElement.style.display = 'none';
        }, 5000);
      }
    },
    showInput(target) {
      if (target === 'title') {
        this.editLectureName = true;
      } else if (target === 'url') {
        this.editHackmdURL = true;
      }
    },
    hideInput(target) {
      if (target === 'title') {
        this.editLectureName = false;
        $('.animation-creation-input#title').val(this.lectureName);
      } else if (target === 'url') {
        this.editHackmdURL = false;
        $('.animation-creation-input#url').val(this.hackmdURL);
      }
    },
    renameLecture() {
      const inputName = $('.animation-creation-input#title').val();
      ajaxJson(
        urls.lecture.rename,
        'POST',
        { name: inputName },
        () => {
          this.lectureName = inputName;
          this.hideInput('title');
          this.showMessage($('.success-message#title'));
          
          // 課程名稱保存成功後開始加載 HackMD 內容
          if (!this.isFromCyberSetup) {
            this.isLoadingHackMD = true;
            this.fetchHackMDContentAndGeneratePrompt().then(() => {
              console.log('HackMD 內容加載完成');
            }).catch(error => {
              console.error('HackMD 內容加載失敗:', error);
              this.isLoadingHackMD = false;
            });
          }
        },
        (jqXHR) => {
          if (jqXHR.responseJSON !== undefined) {
            const err = $('.error-message#title');
            this.showMessage(err);
            err.text(jqXHR.responseJSON.reason);
          }
        },
      );
    },
    updateLectureUrl() {
      const inputUrl = $('.animation-creation-input#url').val();
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
      const inputUrl = $('.animation-creation-input#video-url').val();
      if (inputUrl === this.videoHistory[0]) return;
      if (!this.isValidRtspUrl(inputUrl)) {
        const err = $('.error-message#video-url');
        this.showMessage(err);
        err.text('Invalid URL');
        return;
      }
      ajaxJson(
        urls.lecture.video,
        'POST',
        { url: inputUrl },
        (response) => {
          $('#video-url').prop('src', inputUrl);
          this.videoURL = inputUrl;
          this.hideInput('video-url');
          this.showMessage($('.success-message#video-url'));
          if ('url_history' in response) {
            this.videoHistory = response.video_history;
          }
        },
        (jqXHR) => {
          if (jqXHR.responseJSON !== undefined) {
            const err = $('.error-message#video-url');
            this.showMessage(err);
            err.text(jqXHR.responseJSON.reason);
          }
        },
      );
    },
    isValidHttpUrl(url) {
      let parser;
      parser = document.createElement('a');
      parser.href = url;
      return parser.protocol === 'http:' || parser.protocol === 'https:';
    },
    isValidRtspUrl(url) {
      let parser;
      parser = document.createElement('a');
      parser.href = url;
      return parser.protocol === 'rtsp:';
    },
    setUrl(e) {
      const selectedUrl = e.target.innerText;
      $('.animation-creation-input#url').val(selectedUrl);
    },
    showMessage(elem) {
      elem.show();
      setTimeout(() => {
        elem.hide();
      }, 3000);
    },
    initVpythonEditor() {
      const textarea = document.getElementById('generated-program');
      if (textarea) {
        textarea.value = ''; // 清空初始值
      }
      
      this.vpythonEditor = CodeMirror.fromTextArea(textarea, {
        mode: 'python',
        lineNumbers: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        theme: 'default',
        extraKeys: { 'Ctrl-Space': 'autocomplete' }
      });
    },
    /*reindexIv() {
      this.ivList.forEach((iv) => {
        iv.index = iv.index || 0;
      });
    },*/
    updateGeneratedProgram(program) {
      if (!program || !this.manualSubmit) {
        return;
      }
      
      this.vpythonCode = program;
      
      if (this.vpythonEditor) {
        this.vpythonEditor.setValue(program);
        this.vpythonEditor.refresh();
      }
      
      const generatedProgramTextarea = document.getElementById('generated-program');
      if (generatedProgramTextarea) {
        generatedProgramTextarea.value = program;
      }
    },
  handleGPTError(error, action) {
    console.error(`Error ${action} the program:`, error);
    this.fixingMessage = `Error occurred while ${action} the program: ${error.message}. Please try again.`;

    if (error.message?.includes('CSRF token is missing')) {
        this.fixingMessage = 'CSRF token is missing. Please refresh the page and try again.';
    } else if (error.message?.includes('HTTP error!')) {
        this.fixingMessage = `Server error: ${error.message}. Please try again later.`;
    } else if (error.message?.includes('NetworkError')) {
        this.fixingMessage = 'Network error. Please check your internet connection and try again.';
    }

    this.showErrorMessage(this.fixingMessage);
}
  }
});
