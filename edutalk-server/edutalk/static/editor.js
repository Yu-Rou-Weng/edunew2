/* global __main__:false glowscript_compile:false ajaxJson:false */

let editor;
let student_id = new URLSearchParams(window.location.search).get('student_id');

CodeMirror.commands.autocomplete = function (cm) {
  CodeMirror.showHint(cm, CodeMirror.hint.html);
};

function getVpCode(cb) {
  IDEAjaxGetData(urls.vpCode, { successCallback: cb });
  return 'ok';
}

function setCodeMirror() {
  editor = CodeMirror.fromTextArea(document.getElementById('code'), {
    mode: {
      name: 'python',
      version: 3,
      singleLineStringErrors: false,
    },

    theme: 'twilight',
    indentUnit: 4,
    lineWrapping: true,
    lineNumbers: true,
    styleActiveLine: true,
    matchBrackets: true,

    extraKeys: {
      'Ctrl-Space': 'autocomplete',
    },
    value: `<!doctype html>\n<html>\n  ${document.documentElement.innerHTML}\n</html>`,
  });
}

function updateCodeMirror(newCode) {
  $('#code').show();
  if (newCode) {
    $('#code').val(newCode);
  }

  $('.CodeMirror-wrap').remove();
  setCodeMirror();
  $('#code').hide();
}

function editorInit() {
  // get current user's code
  const successCallback = function (result) {
    const content = $('<textarea></textarea>', { id: 'code', name: 'code' }).val(result.code);
    content.appendTo('#IDE');
    $('#code').hide();
  };
  if (!student_id) getVpCode(successCallback);
  else {
    successCallback({ code: '' });
  }

  // get students list if possible
  IDEAjaxGetData(urls.students, {
    successCallback(students) {
      // init students code list
      const first = $('.current-opt');
      let last = first;
      let selected_opt = last;
      // back to your code
      last.click((e) => {
        $('#studentDropdown').html('Select a Student <span class="caret"></span>');
        $('#commentBtn').hide();
        viewCurrentUserCode();
      });
      // go to student code
      for (const student of students) {
        const opt = $(`<li class="student-opt" value="${student.id}"><a role="button">${student.username}</a></li>`);
        opt.click(function (e) {
          $('#studentDropdown').html(`${$(this).find('a').text()}<span class="caret"></span>`);
          viewStudentCode(student.id);
          $('#commentBtn').show();
        });
        // select student if id match in query param
        if (student_id == student.id) selected_opt = opt;
        opt.insertAfter(last);
        last = opt;
      }
      $('<li role="separator" class="divider"></li>').insertAfter(first);
      // jump to student if query param exist
      if (student_id && selected_opt == first) {
        alert('target student is not exist !');
        student_id = null;
      }
      selected_opt.click();
    },
  });
}

window.__context = {
  glowscript_container: $('#glowscript'),
};

function dai(profile) {
  // dummy
}

function csmPull(df, handler) {
  // dummy
}

function preloadAudio(filename) {
  // dummy
}

function playAudio(filename) {
  // dummy
}
/*async function submitToGptWithError(errorMsg) {
  const fixPrompt = `Please update the program by fixing the following error:\n${errorMsg}\n\nHere's the current program:\n${editor.getValue()}`;
  await animationCreateApp.submitToGpt(true, fixPrompt);
}*/

async function runprog(prog) {
  try {
    console.log('======== Executing Program ========');
    console.log('Program code:', prog.substring(0, 200) + '...');
    
    this.eval(prog);
    await __main__();
    
    console.log('Program executed successfully');
    
  } catch (err) {
    const errMsg = err.message;
    console.group('Runtime Error Details');
    console.log('Error Message:', errMsg);
    console.log('Error Stack:', err.stack);
    console.log('Full Error Code:', prog);
    console.groupEnd();
    
    $('#error-content').text(errMsg);
    $('#error-type').text('Runtime Error');
    $('#error-message').show();
    
    console.log('Preparing to dispatch vpython-error event...');
    
    setTimeout(() => {
      if (!window.animationCreateApp) {
        console.error('animationCreateApp not found - Vue instance may not be ready');
        return;
      }
      
      if (typeof window.animationCreateApp.handleExecutionError !== 'function') {
        console.error('handleExecutionError method not found on animationCreateApp');
        return;
      }
      
      const errorEvent = new CustomEvent('vpython-error', {
        detail: {
          error: errMsg,
          code: prog,
          timestamp: new Date().toISOString()
        }
      });
      
      console.group('Dispatching Error Event');
      console.log('Event type: vpython-error');
      console.log('Error details:', errorEvent.detail);
      console.log('Target:', window);
      console.groupEnd();
      
      window.dispatchEvent(errorEvent);
      console.log('Error event dispatched successfully');
      
    }, 0);
    
    throw err;
  }
}
function execute(code) {
  return new Promise((resolve, reject) => {
    const gsversion = 3.2;
    const compilerUrl = `${urls.vpResource.split('?')[0]}RScompiler.${gsversion}.min.js`;
    code = `GlowScript ${gsversion} VPython\n${code}`;

    window.glowscript_compile = undefined;
    $.ajax({
      url: compilerUrl,
      dataType: 'script',
      cache: true,
      crossDomain: false, // use script tag rather than xhr
      success() {
        if (!window.glowscript_compile) {
          return reject(new Error(`Failed to load compiler from ${compilerUrl}`));
        }

        let embedScript;
        try {
          embedScript = glowscript_compile(code, {
            lang: 'vpython',
            version: gsversion,
          });
        } catch (err) {
          let errMsg = err.message; // gets the error message
          const patt = /line(\\s*)([0-9]*):/;
          const m = errMsg.match(patt);
          if (m !== null) {
            const colonindex = m.index + 4 + m[1].length + m[2].length;
            const n = parseFloat(m[2]) - 1;
            errMsg = `${errMsg.slice(0, m.index)}line ${n}${errMsg.slice(colonindex)}`;
          }
          $('#error-content').text(errMsg);
          $('#error-type').text('Compile Error');
          $('#error-message').show();
          const e = new Error(errMsg);
          e.name = 'Compile Error';
          return reject(e);
        }

        $('#error-message').hide();
        
        try {
          // 修改這部分以正確處理非同步的 runprog
          Promise.resolve(runprog(embedScript))
            .then(() => {
              resolve();
            })
            .catch(runtimeErr => {
              $('#error-content').text(runtimeErr.message);
              $('#error-type').text('Runtime Error');
              $('#error-message').show();
              
              // 確保錯誤事件被正確觸發
              const errorEvent = new CustomEvent('vpython-error', {
                detail: {
                  error: runtimeErr.message,
                  code: embedScript,
                  timestamp: new Date().toISOString()
                }
              });
              window.dispatchEvent(errorEvent);
              
              reject(runtimeErr);
            });
        } catch (runtimeErr) {
          $('#error-content').text(runtimeErr.message);
          $('#error-type').text('Runtime Error');
          $('#error-message').show();
          reject(runtimeErr);
        }
      },
      error(jqXHR, exception) {
        // Ref: https://stackoverflow.com/questions/6792878/jquery-ajax-error-function
        let msg = '';
        if (jqXHR.status === 0) {
          msg = 'Not connect.\n Verify Network.';
        } else if (jqXHR.status === 404) {
          msg = 'Requested page not found. [404]';
        } else if (jqXHR.status === 500) {
          msg = 'Internal Server Error [500].';
        } else if (exception === 'parsererror') {
          msg = 'Requested JSON parse failed.';
        } else if (exception === 'timeout') {
          msg = 'Time out error.';
        } else if (exception === 'abort') {
          msg = 'Ajax request aborted.';
        } else {
          msg = `Uncaught Error.\n${jqXHR.responseText}`;
        }
        return reject(new Error(msg));
      },
    });
  });
}

function saveCode(callback, persist = true) {
  const newCode = editor.getValue();
  $('#code').val(newCode);

  if (!persist) {
    callback();
    return;
  }

  let url;
  if (student_id) {
    if (!confirm("Do you want to overwrite student's code ?")) return;
    url = urls.studentCode(student_id);
  } else {
    url = urls.vpCode;
  }

  const options = {
    data: { code: newCode },
    successCallback: undefined,
  };
  execute(newCode)
    .then(() => {
      options.successCallback = callback;
      IDEAjaxPostData(url, options);
    })
    .catch(console.error);
}

function setAsDefault() {
  const url = student_id ? urls.studentVpDefault(student_id) : urls.vpDefault;
  // save code first
  const callback = function () {
    // send set as default request to server
    console.log('set as default');
    IDEAjaxPostData(url);
  };
  saveCode(callback);
}

function resetCode() {
  const url = student_id ? urls.studentVpReset(student_id) : urls.vpReset;
  const options = {
    successCallback(result) {
      updateCodeMirror(result.code);
      /*
        * Need to refactor this.
        * setCodeMirror will hide #IDE for /tutorial page
        * to prevent #IDE from missing after clicking reset btn, we use $('#IDE').show() here.
        * */
      $('#IDE').show();
    },
  };
  IDEAjaxPostData(url, options);
}

function viewCurrentUserCode() {
  console.log(urls.vpCode);
  const options = {
    successCallback(result) {
      const isHid = $('#IDE').is(':hidden');
      updateCodeMirror(result.code);
      /*
        * Need to refactor this.
        * setCodeMirror will hide #IDE for /tutorial page
        * to prevent #IDE from missing after clicking reset btn, we use $('#IDE').show() here.
        * */
      if (!isHid) $('#IDE').show();
      let queryPos = window.location.href.lastIndexOf('?');
      if (queryPos == -1) queryPos = window.location.href.length;
      history.replaceState({}, null, window.location.href.slice(0, queryPos));
      student_id = null;
    },
  };
  IDEAjaxGetData(urls.vpCode, options);
}

function viewStudentCode(u_id) {
  console.log(urls.studentCode(u_id));
  const options = {
    successCallback(result) {
      const isHid = $('#IDE').is(':hidden');
      updateCodeMirror(result.code);
      /*
        * Need to refactor this.
        * setCodeMirror will hide #IDE for /tutorial page
        * to prevent #IDE from missing after clicking reset btn, we use $('#IDE').show() here.
        * */
      if (!isHid) $('#IDE').show();
      let queryPos = window.location.href.lastIndexOf('?');
      if (queryPos == -1) queryPos = window.location.href.length;
      history.replaceState({}, null, `${window.location.href.slice(0, queryPos)}?student_id=${u_id}`);
      student_id = u_id;
    },
  };
  IDEAjaxGetData(urls.studentCode(u_id), options);
}

function getComment() {
  IDEAjaxGetData(urls.commentUrl(student_id), {
    successCallback(res) {
    // for both textarea and p
      $('#commentText').val(res.comment);
      $('#commentText').text(res.comment);
      $('#commentModal').modal('show');
    },
  });
}

function saveComment() {
  IDEAjaxPostData(urls.commentUrl(student_id), {
    data: { comment: $('#commentText').val() },
    successCallback(res) {
      $('#commentModal').modal('hide');
    },
  });
}

function IDEAjaxPostData(ajaxUrl, options) {
  if (options === undefined) options = { data: {} };

  ajaxJson(
    ajaxUrl,
    'POST',
    options.data,
    (result) => {
      if (options.successCallback) {
        options.successCallback(result);
      } else {
        console.log('success: ', ajaxUrl);
      }
    },
    (result) => {
      console.error('error: ', ajaxUrl);
      console.error('result: ', result.status, result.statusText);
    },
  );
}

function IDEAjaxGetData(ajaxUrl, options) {
  if (options === undefined) options = { data: {} };

  $.ajax({
    url: ajaxUrl,
    type: 'GET',
    dataType: 'json',
    contentType: 'application/json; charset=utf-8',
    data: JSON.stringify(options.data),
    success(result) {
      if (options.successCallback) {
        options.successCallback(result);
      } else {
        console.log('success: ', ajaxUrl);
      }
    },
    error(result) {
      console.error('error: ', ajaxUrl);
      console.error('result: ', result.status, result.statusText);
    },
  });
}
