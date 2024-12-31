/* global updateCodeMirror:false daName:false saveCode:false animationApp:false ajaxJson:false */

/*
 * tutorial.js is the main JS file for Tutotrial Page
 *
 */

/*
 * <current>
 * current specifies the state where the user currently stays
 * It changes when user clicks another pane/ state
 */
let current = 'lecture';

/*
 * <position>
 * position is for lecture pane
 * The following program will save the browsing y index position before the user change state.
 * It is used to go back to the previous position when the user come back to the lecture pane
 */
let position;
let mainHeight;
const isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;

const cyberDeviceUrl = urls.vpIndex;
const videoIndexUrl = urls.videoIndex;
const remoteControlUrl = urls.rcIndex;

$(() => {
  initial();
  $('#lecture-btn').on('click', showLecturePane);
  $('#program-btn').on('click', showProgramPane);
  $('#animation-btn').on('click', showAnimationPane);
  $('#animation-creation-btn').on('click', showAnimationCreationPane);
  console.log('cyber_device', cyberDeviceUrl);
  console.log('remote_control', remoteControlUrl);
});

function initial() {
  /*
   * todo
   * There's somewhere else hide the CodeMirror after the page loaded,
   * for CodeMirror is loading too slow !!
   * Need to fix this
   * */

  // const initState = localStorage.getItem('state');
  // console.log('init_state', initState);
  // if (initState === 'program') {
  //   showProgramPane();
  // } else if (initState === 'animation') {
  //   showAnimationPane();
  // }

  setCurrentState('lecture');
}

function showLecturePane() {
  if (current === 'lecture') {
    return;
  }

  setCurrentState('lecture');
  saveCode(() => {
    $('.main-div').animate({ height: mainHeight }, 1, () => {
    /**
    using animate since $(window).scrollTop(position) doesn't work in firefox
    firefox seems to load iframe much more longer than chrome, which make scrollTop position failed.
    following code detects browser to filter firefox and use show() callback to fix this case.
    * */
      $('html,body').scrollTop(position);
      $('#lecture-content').show();
      $('#IDE').hide();
      $('#animation-content').hide();
      $('#animation-creation').hide();
    });
  }, false);
}

function showProgramPane() {
  if (current === 'program') {
    return;
  }

  saveCurrentLecturePosition();
  setCurrentState('program');
  $('.main-div').height('79%');
  $('#animation-creation').hide();
  $('#lecture-content').hide();
  $('#IDE').show();
  $('#animation-content').hide();
  $(window).scrollTop(0);
  /* For now we update code mirror every time when a user click Program Pane
   * Don't know why for now, but if we use var da_updated = true / false to tell wether
   * CodeMirror need to update or not, it has the problem of being black a while and load slowly.
   * This problem was found when CodeMirror can't find textarea when textarea's status is hide .
   * */
  updateCodeMirror();
}

function showAnimationPane() {
  console.log('current', current);

  if (current === 'animation') {
    return;
  }

  // 檢查是否有GPT生成的代碼需要執行
  if (animationCreateApp && animationCreateApp.gptResponse && 
      !animationCreateApp.isFixingError && !animationCreateApp.debugMode) {
    console.log('Executing generated code in animation pane');
  }

  if (current === 'program' && daName !== '') {
    /*
     * this way is a little bit wierd
     * need to refactor
     */
    saveCode(showAnimationPaneEventHandler, false);
    return;
  }

  showAnimationPaneEventHandler();

  function showAnimationPaneEventHandler() {
    saveCurrentLecturePosition();
    setCurrentState('animation');
    $('.main-div').height('auto');
    $('#lecture-content').hide();
    $('#IDE').hide();
    $('#animation-content').show();
    $('#animation-creation').hide();
    $(window).scrollTop(0);

    // 如果是從animation-creation頁面自動跳轉過來
    if (animationCreateApp && animationCreateApp.gptResponse && 
        !animationCreateApp.isFixingError && !animationCreateApp.manualSubmit) {
      console.log('Auto redirected from animation creation');
      
      // 檢查並執行生成的代碼
      if (animationCreateApp.vpythonCode) {
        try {
          // 更新編輯器內容
          if (typeof updateCodeMirror === 'function') {
            updateCodeMirror(animationCreateApp.vpythonCode);
          }
          
          // 保存代碼
          if (typeof saveCode === 'function') {
            saveCode(() => {
              console.log('Generated code saved successfully');
            }, false);
          }

          // 執行動畫
          if (typeof execute === 'function') {
            execute(animationCreateApp.vpythonCode);
          }
        } catch (error) {
          console.error('Error executing generated code:', error);
        }
      }
    }
  }
}
/*function showAnimationCreationPane() {
    saveCurrentLecturePosition();
    setCurrentState('animation-creation');
    $('.main-div').height('auto');
    $('#lecture-content').hide();
    $('#IDE').hide();
    $('#animation-content').hide();
    $('#animation-creation-content').show();
    $(window).scrollTop(0);
    // Initialize or clear fields if necessary
    $('#title').val('');
    $('#variable').val('radius_i');  // Default to first option
    $('#gpt-window').val('');
}*/
function showAnimationCreationPane() {
  if (current === 'animation-creation') {
    return;
  }

  saveCurrentLecturePosition();
  setCurrentState('animation-creation');
  $('.main-div').height('auto');  
  $('#lecture-content').hide();
  $('#IDE').hide();
  $('#animation-content').hide();
  $('#animation-creation').show(); 
  $(window).scrollTop(0);
}

function setIframeUrl(target) {
  /*
   * Since DA keeps pulling data from iottalk server,
   * which makes browser busy sending HTTP Requests,
   * we create a function that make DA shut up by removing the iframe url
   *
   * */

  if (target === 'animation') {
    $('#device-iframe').attr('src', cyberDeviceUrl);
    $('#video-iframe').attr('src', videoIndexUrl);
  } else {
    $('#device-iframe').attr('src', '');
    $('#video-iframe').attr('src', '');
  }
}

function saveCurrentLecturePosition() {
  if (current === 'lecture') {
    position = $(window).scrollTop();
    mainHeight = $('.main-div').height();
  }
}

function setCurrentState(target) {
  /* setNavigationBar
   * 1. make target 'active' by adding class
   * 2. add IDE button on top of navbar when pane is 'Program'
   */
  setNavigationBar(target);
  setIframeUrl(target); // set iframe url if pane is 'Animation'

  localStorage.setItem('state', target);
  current = target;
  if (target === 'animation' && animationApp.dataSource !== 'Historical Data') {
    ajaxJson(
      urls.m2Bind(),
      'POST',
      {},
      () => console.log('m2 device bind success'),
      () => console.error('m2 device bind failed'),
    );
  }
  if (target !== 'animation') {
    ajaxJson(
      urls.vpUnBind(),
      'POST',
      {},
      () => console.log('vp unbind success'),
      () => console.error('vp unbind failed'),
    );
  }

  const action = (target === 'animation') ? 'bind' : 'unbind';
  ajaxJson(
    urls.lecture[action],
    'POST',
    {},
    () => console.log(`simple logger ${action} success`),
    () => console.error(`simple logger ${action} failed`),
  );
}

function setNavigationBar(target) {
  /*
   * 1. set target as active on navigation bar
   * */
  $(`#${current}-btn`).removeClass('active');
  $(`#${target}-btn`).addClass('active');
}