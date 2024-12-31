const animationCreateApp = new Vue({
    el: '#animation-creation',
    data: {
      csrfToken: document.querySelector('meta[name="csrf-token"]').getAttribute('content'),
      currentType: 'value',
      showSubmitButton: false,
      defaultGptPrompt: '',
      selectedIDF: {
        name: '',
        dimensions: 1,
        type: 'value'
      },
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
      globalIvList: {}, // 這裡需要從後端獲取，或者在 mounted 中初始化
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
      csrfToken: '',
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
      fixAttempts: 0,
      maxFixAttempts: 10,
      debugMode: false,
      autoRedirectEnabled: true,
    },
    watch: {
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
      isGptResponse() {
        const marker = "Create a VPython animation to illustrate the following physics experiment:";
        return this.gptPrompt.includes(marker);
      },
      showRenameBtn() {
        return this.isEditMode; // 假設您有一個 isEditMode 的狀態
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
      this.$nextTick(() => {
        const lectureElement = document.querySelector('.col-sm-2 h5');
        const lectureNameElement = document.querySelector('.lecture-name');
        if (lectureElement && lectureNameElement) {
          const computedStyle = window.getComputedStyle(lectureElement);
          lectureNameElement.style.fontSize = computedStyle.fontSize;
          lectureNameElement.style.fontWeight = computedStyle.fontWeight;
        }
      });
      // 分析当前的 URL 来取得 lectureId
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
      
      // 顯示加載提示
      this.isLoadingHackMD = true;
      
      // 獲取 HackMD 內容並生成最終 PROMPT
      this.fetchHackMDContentAndGeneratePrompt().then(() => {
        console.log("Final gptPrompt after fetching:", this.gptPrompt);
      });
    
      this.updateTypeSelectorWithForceUpdate(); 
      this.updateTypeSelector(); 
      this.initVpythonEditor();
    },
    
    methods: {
      async fetchHackMDContentAndGeneratePrompt() {
        try {
          // 發送請求以獲取 HackMD 內容
          const markdownResponse = await fetch(`/edutalk/new-lecture${this.lectureId}/hackmd/markdown`);
          if (!markdownResponse.ok) {
            throw new Error(`HTTP error! status: ${markdownResponse.status}`);
          }
          
          const data = await markdownResponse.json();
          const fetchedMarkdown = data.markdown;
      
          if (!fetchedMarkdown) {
            throw new Error('No markdown content received');
          }
        
          console.log('Fetched Markdown:', fetchedMarkdown);
          
          // 構建發送至 GPT API 的 prompt
          const gptApiPrompt = `請用英文敘述下面是在進行何種物理運動, 過濾掉敘述程式撰寫的部分:\n${fetchedMarkdown}`;
          
          // 發送 GPT API 請求
          const gptApiResponse = await fetch(`/edutalk/new-lecture/${this.lectureId}/submit_to_gpt`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': this.csrfToken,
            },
            body: JSON.stringify({
              prompt: gptApiPrompt,
              mode: 'initial'
            })
          });
      
          if (!gptApiResponse.ok) {
            throw new Error(`HTTP error! status: ${gptApiResponse.status}`);
          }
        
          const gptApiResult = await gptApiResponse.json();
      
          // 確認 GPT API 結果
          console.log('GPT API Result:', gptApiResult);
      
          // 構建最終的 prompt，將你要求的部分標記為紅色
          const finalPrompt = `1. Screen Settings:\n\nSet the canvas width to 700 and height to 400. Do not change the canvas size.\n\n\n                                    2. Object Motion & Parameter Settings:\n\nCreate a VPython animation to illustrate the following physics experiment:<br><span style="color:red;">${gptApiResult.program}</span>`;
      
          console.log("最終 PROMPT:", finalPrompt);
      
          // 更新 this.gptPrompt
          this.gptPrompt = finalPrompt;
      
        } catch (error) {
          console.error("Error processing markdown and submitting to GPT:", error);
          // 發生錯誤時設置 gptPrompt 為錯誤訊息
          this.gptPrompt = `Error: ${error.message}`;
        } finally {
          // 隐藏加载提示
          this.isLoadingHackMD = false;
        }
      },
    
      async processFetchedMarkdownAndSubmit() {
        try {
          // 使用正確的端點來獲取 markdown 內容
          const markdownResponse = await fetch(`/edutalk/new_lecture/${this.lectureId}/hackmd/markdown`);
          if (!markdownResponse.ok) {
            throw new Error(`HTTP error! status: ${markdownResponse.status}`);
          }
          const data = await markdownResponse.json();
          const fetchedMarkdown = data.markdown;
          
          // 檢查是否成功獲取到 markdown 內容
          if (!fetchedMarkdown) {
            throw new Error('No markdown content received');
          }
      
          console.log('Fetched Markdown:', fetchedMarkdown);
          
          // 定義要過濾掉程式撰寫部分的 prompt
          const gptApiPrompt = `請用英文敘述下面是在進行何種物理運動, 過濾掉敘述程式撰寫的部分:\n${fetchedMarkdown}`;
          
          // 發送到 GPT API
          const gptApiResponse = await fetch(`/edutalk/new_lecture/${this.lectureId}/submit_to_gpt`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': this.csrfToken,
            },
            body: JSON.stringify({
              prompt: gptApiPrompt,
              mode: 'initial'
            })
          });
      
          if (!gptApiResponse.ok) {
            throw new Error(`HTTP error! status: ${gptApiResponse.status}`);
          }
      
          const gptApiResult = await gptApiResponse.json();
          
          // 構建最終的 PROMPT，將前面部分加入 GPTAPI 的回覆
          const finalPrompt = `
      1. Screen Settings:\n
      Set the canvas width to 700 and height to 400. Do not change the canvas size.\n\n
      2. Object Motion & Parameter Settings:\n
      Create a VPython animation to illustrate the following physics experiment:\n\n
      ${gptApiResult.program}
          `;
          
          // 將最終的 prompt 顯示在 console 並更新到 Prompt Window
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
          this.newVariableName = ''; // 清空輸入框
          this.updateModalContent({ program: JSON.stringify({ controlled_variables: this.cyberVariables }) });
        }
      },
      updateIDFButtonText() {
        this.$nextTick(() => {
            console.log(`Attempting to update IDF button text for ${this.currentVariable}`);
            console.log(`Selected IDFs:`, JSON.stringify(this.selectedIDFs));
            const buttonSelector = `#idf-btn-${this.currentVariable.replace(/\s+/g, '')}`;
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
        this.updateTypeSelector(); // 先呼叫 updateTypeSelector 設定 type
        this.$forceUpdate(); // 強制 Vue 重新渲染，確保下拉框即時顯示最新的選擇值
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
        this.$forceUpdate(); // 確保 UI 立即更新
      },
      
      closeIDFDropdown() {
        const dropdown = document.querySelector('.idf-dropdown');
        if (dropdown) {
          dropdown.remove();
        }
      },
      openAddDimensionModal() {
        // 打开模态框之前设置默认值
        if (this.numberOfDimensions === 1) {
          this.settingIv.type = 'value';
        } else if (this.numberOfDimensions === 3) {
          this.settingIv.type = 'array';
        } else if (this.numberOfDimensions === 2 || (this.numberOfDimensions >= 4 && this.numberOfDimensions <= 9)) {
          this.settingIv.type = 'array';
        }
        // 打开模态框逻辑
        $('#addDimensionModal').modal('show');
      },  
      saveIDFSelection(idfName) {
        console.log(`Saving IDF selection: ${idfName} for ${this.currentVariable}`);
        this.$set(this.selectedIDFs, this.currentVariable, idfName);
        console.log('Updated selectedIDFs:', JSON.stringify(this.selectedIDFs));
        this.updateIDFButtonText();
        this.closeIDFDropdown();
    
        // 直接更新按钮文本
        const idfButton = document.querySelector(`#idf-btn-${this.currentVariable.replace(/\s+/g, '')}`);
        if (idfButton) {
            idfButton.textContent = idfName;
            console.log(`Directly updated IDF button text to: ${idfName}`);
        } else {
            console.error(`IDF button not found for ${this.currentVariable}`);
        }
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
        modal.removeAttribute('inert');  // 移除 inert 屬性，允許交互
        modal.setAttribute('aria-hidden', 'false');  // 設置 aria-hidden 為 false
        $('#cyberVariableModal').modal('show');
      },
      hideCyberVariableModal() {
        const modal = document.getElementById('cyberVariableModal');
        modal.setAttribute('inert', 'true');  // 添加 inert 屬性，禁止交互
        modal.setAttribute('aria-hidden', 'true');  // 設置 aria-hidden 為 true
        $('#cyberVariableModal').modal('hide');
      },
      connectToCyberVariable() {
        console.log("connectToCyberVariable method called");
        const marker = "Create a VPython animation to illustrate the following physics experiment:";
        const index = this.gptPrompt.indexOf(marker);
    
        if (index !== -1) {
            const experimentDescription = this.gptPrompt.substring(index + marker.length).trim();
            console.log("Extracted experiment description:", experimentDescription);
    
            //const prompt = `In this experiment, what variables can be controlled? Just give the variable names. No need to explain them. Please provide the returned content in JSON format.\n\n${experimentDescription}`;
            const prompt = `Identify all the variables that can be controlled in this experiment. Please return only the variable names in JSON format, without any explanation.\n\n${experimentDescription}`;
            //const prompt = `List **all** the variables that can be controlled in this experiment. Ensure that **no variable is omitted**. Please return the variable names in JSON format, and **double-check the list to confirm all controllable variables are included**. No explanation is needed.\n\n${experimentDescription}`;
            console.log("Prompt to be sent to GPT:", prompt);
    
            // Display loading message in modal
            const modalBody = document.querySelector('#cyberVariableModal .modal-body');
            if (modalBody) {
                modalBody.innerHTML = '<p>Loading controllable variables...</p>';
            }
            $('#cyberVariableModal').modal('show');
    
            fetch(`/edutalk/new_lecture/${this.lectureId}/submit_to_gpt`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.csrfToken
                },
                body: JSON.stringify({
                    prompt: prompt,
                    mode: 'initial'
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log("GPT API Response:", data);
                if (data.program) {
                    try {
                        const parsedData = JSON.parse(data.program);
                        this.cyberVariables = (parsedData && parsedData.controlled_variables)
                            ? parsedData.controlled_variables.filter(v =>
                                !v.toLowerCase().includes('time') &&
                                !v.toLowerCase().includes('duration')
                            )
                            : [];
                        console.log("Filtered cyberVariables:", this.cyberVariables);
                        this.updateModalContent(data);
                    } catch (error) {
                        console.error('Error parsing GPT response:', error);
                        this.updateModalContent({ error: 'An error occurred while processing the GPT response.' });
                    }
                } else {
                    console.error("No program in GPT response");
                    this.updateModalContent({ error: 'No valid response from GPT.' });
                }
            })
            .catch(error => {
                console.error("Error in fetch:", error);
                this.updateModalContent({ error: 'An error occurred while communicating with the server.' });
            });
        } else {
            console.error('Marker text not found in the prompt');
            this.updateModalContent({ error: 'Invalid prompt format. Please make sure the prompt contains the correct marker.' });
            $('#cyberVariableModal').modal('show');
        }
    },
    saveCyberVariables() {
      let cyberInputMappingInfo = "\n\n3. Cyber Input Variable Mapping Information:\n";
  
      const selectedVariables = this.cyberVariables.filter(v =>
          document.getElementById(v.replace(/\s+/g, '')).checked
      ).map(v => {
          const savedData = this.globalIvList[v] || {};
          const idf = this.selectedIDFs[v] || '';
          let dimensionValues = [];
  
          if (['Acceleration', 'Gyroscope', 'Magnetometer', 'Orientation'].includes(savedData.sensor)) {
              dimensionValues = [savedData.x0 || 0, savedData.x1 || 0, savedData.x2 || 0];
          } else if (savedData.sensor === 'Range Slider') {
              dimensionValues = [savedData.default || 5];
          } else if (['Input Box (Number)', 'Input Box (String)'].includes(savedData.sensor)) {
              dimensionValues = [savedData.default || 0];
          }
  
          // 正確生成初始值邏輯，根據物理特徵綁定的生成方式
          let initialValue = '';
          if (this.selectedIDF.dimensions === 1) {
              initialValue = `${dimensionValues[0]}`;
          } else if (this.selectedIDF.dimensions === 3 && this.selectedIDF.type === 'vector') {
              initialValue = `[${dimensionValues.join(', ')}]`;
          } else {
              initialValue = `[${dimensionValues.join(', ')}]`;
          }
  
          return {
              name: v,
              idf: idf,
              sensor: savedData.sensor || '',
              initialValue: initialValue
          };
      });
  
      // Consolidate all selected variables into the prompt
      selectedVariables.forEach((variable, index) => {
          cyberInputMappingInfo += `\n(${index * 2 + 1}) ${variable.name} is mapped to the variable named ${variable.idf} with an initial value set to a ${this.selectedIDF.dimensions}-dimensional ${this.selectedIDF.type} ${variable.initialValue}`;
          cyberInputMappingInfo += `\n(${index * 2 + 2}) When the value of ${variable.idf} changes, let the animation rerun to the starting point and start with the updated ${variable.name}.\n`;
      });
  
      // Add the variable mapping info to the GPT prompt
      //this.gptPrompt += cyberInputMappingInfo;
  
      // Close the modal and enable the submit button
      $('#cyberVariableModal').modal('hide');
      this.showSubmitButton = true;
      this.isFirstSubmission = true;
  
      console.log("Updated gptPrompt:", this.gptPrompt);
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
      async fetchSessionIds() {
        const response = await fetch(`/edutalk/new_lecture/${this.lectureId}/get_sessions`);
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
          const response = await fetch(`/edutalk/new_lecture/${this.lectureId}/get_serial_numbers?session_id=${this.selectedSessionId}`);
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
          const response = await fetch(`/edutalk/new_lecture/${this.lectureId}/get_log?session_id=${this.selectedSessionId}&serial_number=${this.selectedSerialNumber}`);
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
        const response = await fetch(`/edutalk/new_lecture/${this.lectureId}/get_log?session_id=${this.selectedSessionId}&serial_number=${this.selectedSerialNumber}`);
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
        const url = `/edutalk/new_lecture/${this.lectureId}/hackmd/markdown`;
    
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
      async compileAndRunProgram(code) {
        try {
          await execute(code);
          this.vpythonCode = code;
          this.updateGeneratedProgram(code);
          this.fixAttempts = 0;
          this.isFixingError = false;
          this.needRewrite = false;
          this.fixingMessage = '';
          console.log("Program executed successfully, no errors.");
          
          editor.setValue(code);
          saveCode(() => {
            console.log('Code saved successfully!');
          });
      
          // Hide runtime error display
          $('#runtime-error').hide();
      
          if (this.autoRedirectEnabled && !this.debugMode && !this.isFixingError) {
            this.triggerAutoRedirect();
          }
        } catch (error) {
          console.error('Error executing program:', error);
          const errorMessage = this.extractErrorMessage(error.message);
          console.log(`Execution error: ${errorMessage}`);
          
          if (this.debugMode && this.currentMode === 'fix_error') {
            // In debug mode and fix_error mode, display the error next to the generated program
            $('#runtime-error').text(`Runtime Error: ${errorMessage}`).show();
          } else if (!this.debugMode) {
            this.isFixingError = true;
            this.fixAttempts++;
            this.fixingMessage = `Waiting for the runtime error to be fixed: Round ${this.fixAttempts}`;
            await this.fixErrorAndResubmit(errorMessage, code);
          }
        }
      },
      connectToCyberVariable() {
        console.log("connectToCyberVariable method called");
        const marker = "Create a VPython animation to illustrate the following physics experiment:";
        const index = this.gptPrompt.indexOf(marker);
    
        if (index !== -1) {
            const experimentDescription = this.gptPrompt.substring(index + marker.length).trim();
            console.log("Extracted experiment description:", experimentDescription);
    
            const prompt = `In this experiment, what variables can be controlled? Just give the variable names. No need to explain them. Please provide the returned content in JSON format.\n\n${experimentDescription}`;
            console.log("Prompt to be sent to GPT:", prompt);
    
            
            const modalBody = document.querySelector('#cyberVariableModal .modal-body');
            if (modalBody) {
                modalBody.innerHTML = '<p>Loading controllable variables...</p>';
            }
            $('#cyberVariableModal').modal('show');
    
            fetch(`/edutalk/new_lecture/${this.lectureId}/submit_to_gpt`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.csrfToken
                },
                body: JSON.stringify({
                    prompt: prompt,
                    mode: 'initial'
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log("GPT API Response:", data);
                if (data.program) {
                    try {
                        
                        let gptProgram = data.program.replace(/```json/g, '').replace(/```/g, '').trim();
    
                        
                        const parsedData = JSON.parse(gptProgram);
                        
                        this.cyberVariables = (parsedData && parsedData.controlled_variables) 
                            ? parsedData.controlled_variables.filter(v => 
                                !v.toLowerCase().includes('time') && 
                                !v.toLowerCase().includes('duration')
                              )
                            : [];
                        
                        console.log("Filtered cyberVariables:", this.cyberVariables);
                        this.updateModalContent(data);
                    } catch (error) {
                        console.error('Error parsing GPT response:', error);
                        this.updateModalContent({ error: 'An error occurred while processing the GPT response.' });
                    }
                } else {
                    console.error("No program in GPT response");
                    this.updateModalContent({ error: 'No valid response from GPT.' });
                }
            })
            .catch(error => {
                console.error("Error in fetch:", error);
                this.updateModalContent({ error: 'An error occurred while communicating with the server.' });
            });
        } else {
            console.error('Marker text not found in the prompt');
            this.updateModalContent({ error: 'Invalid prompt format. Please make sure the prompt contains the correct marker.' });
            $('#cyberVariableModal').modal('show');
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
      
      this.currentVariable = variable;
      const idfName = this.selectedIDFs[variable] || variable;
      
      this.selectedIDF = {
        name: idfName,
        dimensions: 1,
        type: 'value'
      };
    
    
      if (['Gyroscope_I', 'Magnetometer_I', 'Orientation_I', 'Acceleration_I'].includes(idfName)) {
        this.selectedIDF.dimensions = 3;
        this.selectedIDF.type = 'vector';
      } else if (idfName === this.newVariableName) {
        this.selectedIDF.dimensions = this.numberOfDimensions;
        this.selectedIDF.type = this.settingIv.type;
      }
  
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
    
      console.log(`選擇的 IDF 詳情: ${JSON.stringify(this.selectedIDF)}`);
    
      this.$nextTick(() => {
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
  
      this.$set(this.globalIvList, this.currentVariable, {
          sensor: this.settingIv.params[0].sensor,
          device: this.settingIv.params[0].device,
          ...this.settingIv.params[0]
      });
  
      console.log(`Saved variable ${this.currentVariable} with sensor: ${this.settingIv.params[0].sensor}, device: ${this.settingIv.params[0].device}`);
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
    updateModalContent(data) {
      console.log("Updating modal content with data:", data);
    
      const modalBody = document.querySelector('#cyberVariableModal .modal-body');
      if (modalBody) {
        if (data.error) {
          modalBody.innerHTML = `<p class="text-danger">${data.error}</p>`;
        } else {
          try {
            // Clean up the response from GPT by removing the backticks and "json" keyword
            let gptProgram = data.program.replace(/```json/g, '').replace(/```/g, '').trim();
            
            // Log the cleaned GPT response
            console.log("Cleaned GPT Program:", gptProgram);
    
            // Parse the cleaned response
            const parsedData = JSON.parse(gptProgram);
    
            // Extract and filter the controllable variables
            const filteredVariables = (parsedData && parsedData.controlled_variables)
              ? parsedData.controlled_variables.filter(v => 
                  !v.toLowerCase().includes('time') && 
                  !v.toLowerCase().includes('duration')
                )
              : [];
    
            // Make a shallow copy of the array to avoid reactivity issues
            this.cyberVariables = [...filteredVariables];
    
            console.log("Filtered cyberVariables:", this.cyberVariables);
    
            // Generate the variable list HTML for the modal
            let variableListHTML = this.cyberVariables.map(v => `
              <div class="form-check d-flex align-items-center mb-2">
                <input class="form-check-input" type="checkbox" id="${v.replace(/\s+/g, '')}" @change="toggleButtons('${v}')">
                <label class="form-check-label mr-2" for="${v.replace(/\s+/g, '')}">${v}</label>
                <div id="buttons-${v.replace(/\s+/g, '')}" style="display: none;">
                  <button class="btn btn-sm btn-secondary mr-2 idf-list-btn" data-variable="${v}" id="idf-btn-${v.replace(/\s+/g, '')}">${this.selectedIDFs[v] || 'IDF List'}</button>
                  <button class="btn btn-sm btn-secondary sensor-select-btn" data-variable="${v}">Sensor Selection</button>
                </div>
              </div>
            `).join('');
    
            modalBody.innerHTML = `
              <p>Controllable Variables:</p>
              ${variableListHTML}
            `;
    
            this.$nextTick(() => {
              this.addCheckboxListeners();
              this.addIDFButtonListeners();
              this.addSensorButtonListeners();
            });
    
          } catch (error) {
            console.error('Error parsing GPT response:', error);
            modalBody.innerHTML = `<p class="text-danger">An error occurred while processing the GPT response: ${error.message}</p>`;
          }
        }
      } else {
        console.error("Modal body element not found");
      }
    
      // Ensure the selected IDFs are initialized
      this.cyberVariables.forEach(v => {
        if (!this.selectedIDFs.hasOwnProperty(v)) {
          this.$set(this.selectedIDFs, v, 'IDF List');
        }
      });
    
      console.log('Updated modal content. Current selectedIDFs:', JSON.stringify(this.selectedIDFs));
      
      $('#cyberVariableModal').modal('show');
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
        }
        this.needRewrite = false;
  
        if (!this.isFixingError) {
          setTimeout(() => {
            const animationBtn = document.getElementById('animation-btn');
            if (animationBtn) {
              animationBtn.click();
            }
          }, 3000);
        }
      },
      async fixErrorAndResubmit(errorMessage, code) {
        if (this.fixAttempts >= this.maxFixAttempts) {
            this.updateGeneratedProgram("# Gpt-4 failed to generate your program without errors");
            this.needRewrite = true;
            this.isSubmittingToGpt = false;
            this.fixingMessage = 'Gpt-4 cannot fix errors. Please modify your prompt.';
            return;
        }
        console.log(`Starting fix attempt ${this.fixAttempts}`);
        const fixPrompt = `Please fix the following error in the program:\n${errorMessage}\n\nHere's the current program:\n${code}`;
        console.log("Sending fix prompt to GPT:", fixPrompt);
        
        await this.submitToGpt(true, fixPrompt);
    },
      extractErrorMessage(errorText) {
        return errorText;
      },
      async submitToGpt() {
        this.manualSubmit = true;
        this.isSubmittingToGpt = true;
        this.isFixingError = false;
        this.needRewrite = false;
        this.gptResponse = null;
        this.fixAttempts = 0;
    
        try {
       
            if (!this.gptPrompt.trim()) {
                throw new Error("Prompt is empty");
            }
    
            let cleanedPrompt = this.gptPrompt.replace(/```python/g, '').replace(/```/g, '').trim();
    
            const url = `/edutalk/new_lecture/${this.lectureId}/submit_to_gpt`;
            const requestBody = {
                prompt: cleanedPrompt,
                mode: 'initial'
            };
    
            const response = await this.sendRequestToGPT(url, requestBody);
            this.handleGPTResponse(response, requestBody);
    
        } catch (error) {
            this.handleGPTError(error, 'generating');
        } finally {
            this.isSubmittingToGpt = false;
            this.manualSubmit = false;
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
  
  
  async handleGPTResponse(data, requestBody) {
      this.saveGptInteraction(requestBody.prompt, data.program, requestBody.mode);
      this.vpythonCode = data.program;
      this.gptResponse = data;
  
      const generatedProgramTextarea = document.getElementById('generated-program');
      if (generatedProgramTextarea) {
          generatedProgramTextarea.value = data.program;
      }
  
      await this.compileAndRunProgram(data.program);
  },
  
  handleGPTError(error, action) {
      console.error(`Error ${action} the program:`, error);
      this.fixingMessage = `Error occurred while ${action} the program: ${error.message}. Please try again.`;
  
      if (error.message.includes('CSRF token is missing')) {
          this.fixingMessage = 'CSRF token is missing. Please refresh the page and try again.';
      } else if (error.message.includes('HTTP error!')) {
          this.fixingMessage = `Server error: ${error.message}. Please try again later.`;
      } else if (error.message.includes('NetworkError')) {
          this.fixingMessage = 'Network error. Please check your internet connection and try again.';
      }
  
      this.showErrorMessage(this.fixingMessage);
  },
      saveGptInteraction(input, output, mode) {
        const interaction = {
          mode: mode,
          input: input,
          output: output
        };
      
        console.log("GPT Interaction:", JSON.stringify(interaction, null, 2));
      
        fetch(`/edutalk/new_lecture/${this.lectureId}/save_gpt_interaction`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
          },
          body: JSON.stringify(interaction),
          credentials: 'include'
        }).then(response => response.json())
      .then(data => {
        console.log("Save interaction response:", data);
        if (data.new_session_id) {
          this.updateCurrentSessionId(data.new_session_id);
        }
        if (data.new_serial_number) {
          this.fetchSerialNumbers();
        }
      })
      .catch(error => console.error("Error saving interaction:", error));
        },
        async checkNextLogEntry() {
          if (!this.selectedSessionId || !this.selectedSerialNumber) return false;
          
          const currentIndex = this.serialNumbers.findIndex(item => item.value == this.selectedSerialNumber);
          if (currentIndex === -1 || currentIndex === this.serialNumbers.length - 1) return false;
          
          const nextSerialNumber = this.serialNumbers[currentIndex + 1].value;
          const response = await fetch(`/edutalk/new_lecture/${this.lectureId}/get_log?session_id=${this.selectedSessionId}&serial_number=${nextSerialNumber}`);
          const nextLogData = await response.json();
          
          return nextLogData.mode === 'fix_error';
        },      
        async submitToGptWithModification() {
          this.manualSubmit = true;
          this.isSubmittingToGpt = true;
          this.isFixingError = false;
          this.needRewrite = false;
          this.gptResponse = null;
          this.fixAttempts = 0;
        
          try {
            const url = `/edutalk/new_lecture/${this.lectureId}/submit_to_gpt`;
            let prompt, mode;
        
            if (this.vpythonCode) {
              // If there's existing code, use modification mode
              prompt = `Please update the following program based on this instruction: ${this.gptPrompt}\n\n${this.vpythonCode}`;
              mode = 'modification';
            } else {
              // If there's no existing code, use initial mode
              prompt = this.gptPrompt;
              mode = 'initial';
            }
        
            // Ensure prompt is not empty
            if (!prompt.trim()) {
              throw new Error("Prompt is empty");
            }
        
            const requestBody = {
              prompt: prompt,
              mode: mode
            };
        
            console.log('Sending request to:', url);
            console.log('Request body:', JSON.stringify(requestBody, null, 2));
        
            const response = await this.sendRequestToGPT(url, requestBody);
            
            // Extract only the Python code from the GPT-4 response
            const code = this.extractPythonCode(response.program);
            await this.handleGPTResponse({ program: code }, requestBody);
        
          } catch (error) {
            this.handleGPTError(error, 'processing');
          } finally {
            this.isSubmittingToGpt = false;
            this.manualSubmit = false;
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
          // Check if the returned code is valid before attempting to execute
          if (data.program && data.program.trim().length > 0) {
            this.saveGptInteraction(requestBody.prompt, data.program, requestBody.mode);
            this.vpythonCode = data.program;
            this.gptResponse = data;
        
            const generatedProgramTextarea = document.getElementById('generated-program');
            if (generatedProgramTextarea) {
              generatedProgramTextarea.value = data.program;
            }
        
            await this.compileAndRunProgram(data.program);
          } else {
            throw new Error("Received empty or invalid program from GPT");
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
        this.vpythonEditor = CodeMirror.fromTextArea(document.getElementById('generated-program'), {
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
        this.vpythonCode = program;
        if (this.vpythonEditor) {
          this.vpythonEditor.setValue(program);
        }
      }
    }
  });
  