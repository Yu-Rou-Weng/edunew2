/* global dev:false __main__:false glowscript_compile:false profile:false
input_variables:false output_variables:false vec:false vector:false */
const dai = async function (profile) {
  /*
  profile = {
    'dm_name': <DeviceModel name>,
    'idf_list': [ [<callback function with DeviceFeature name> , [<unit>, ...]], ...],
    'odf_list': [ [<callback function with DeviceFeature name> , [<unit>, ...]], ...],
  }
  */

  let isReady = false;

  function onRegister() {
    const url = urls.vpBind(this.appID);
    $.ajax({
      type: 'POST',
      headers: { 'x-csrf-token': csrf.token },
      url,
      success() {
        console.log('device binding success');
        isReady = true;
      },
      error(e) {
        console.error('device binding failed');
        if (e.status == 500) alert('Unknown Error: Please try again later.');
        else if (e.responseJSON === undefined) alert(e.responseText);
        else if (e.responseJSON.message) alert(e.responseJSON.message);
        else if (e.responseJSON.actuator_errors) alert(e.responseJSON.actuator_errors.join('\r\n'));
        isReady = true;
      },
    });
  }

  window.da = new iottalkjs.DAI({
    apiUrl: urls.csmUrl,
    deviceModel: profile.dm_name,
    deviceName: dev,
    pushInterval: 0,
    idfList: profile.idf_list,
    odfList: profile.odf_list,
    onRegister,
  });
  window.da.run();

  while (!isReady || !Object.values(window.da.flags).every((flag) => flag === true)) {
    await new Promise((r) => setTimeout(r, 50));
  }

  await new Promise((r) => setTimeout(r, 2000));
};

async function setup() {
  await dai(profile);
}

/* ==Basic== */
const audio = {};

const preloadAudio = function (filename) {
  if (audio[filename] === undefined) {
    audio[filename] = new Audio(`/da/vp/audio/${filename}`);
  }
};

/* exported playAudio */
function playAudio(filename) {
  preloadAudio(filename);
  if (audio[filename] !== undefined) {
    audio[filename].play();
  }
}

async function runprog(prog) {
  try {
    // intercept listener functions
    for (const variable of input_variables) {
      const listener = `on_${variable}`;
      const pattern = new RegExp('"use strict";');
      prog = prog.replace(pattern, `"use strict";window.${listener
      }=typeof(${listener}) == "function"?${listener}:undefined;`);
    }
    // intercept output variables
    for (const variable of output_variables) {
      // remove declaration from program
      const pattern = new RegExp(`, ${variable.name}`);
      prog = prog.replace(pattern, '');
      // intercept output variables
      const idfName = variable.idf[0];
      intercept(
        variable,
        this,
        (val) => {
          if (window.da && window.da.flags[idfName]) {
            window.da.dan.push(idfName, val);
          }
        },
      );
    }
    // run
    this.eval(prog);
    await setup();
    await __main__();
  } catch (err) {
    console.error('Runtime Error: ', err.message);
    
    const errorEvent = new CustomEvent('vpython-error', {
      detail: {
        error: err.message,
        code: prog,
        timestamp: new Date().toISOString()
      }
    });
    window.dispatchEvent(errorEvent);
    
    throw err;
  }
}

const execute = function (code) {
  // process global
  for (const v of output_variables) {
    code = `global ${v.name}\n${code}`;
  }
  for (const variable of input_variables) {
    code = `global ${variable}\n${code}`;
  }

  const gsversion = 3.2;
  code = `GlowScript ${gsversion} VPython\n${code}`;

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
    console.error('Compile Error: ', errMsg);
    return;
  }
  runprog(embedScript);
};

const fetchCode = function (url) {
  const codeSection = $('#code', parent.document);
  if (codeSection.length > 0) {
    execute(codeSection.val());
  } else {
    $.getJSON(url)
      .done((data) => {
        console.log(data);
        execute(data.code);
      })
      .fail((jqxhr, settings, execption) => {
        console.error(execption);
      });
  }
};

window.__context = {
  glowscript_container: $('#glowscript'),
};

$(() => {
  fetchCode(urls.vpCode);
});

function eqSet(as, bs) {
  return as.size === bs.size && all(isIn(bs), as);
}

function all(pred, as) {
  for (const a of as) if (!pred(a)) return false;
  return true;
}

function isIn(as) {
  return function (a) {
    return as.has(a);
  };
}

// listen to array[index] assigment
function arrayChangeHandler(callback) {
  return {
    get(target, property) {
      if (property >= target.length || property < 0) {
        return false;
      }
      return target[property];
    },
    set(target, property, value, receiver) {
      target[property] = value;
      callback([...target]);
      return true;
    },
    deleteProperty(target, property) {
      return false;
    },
  };
}

// listen to array=[] assigment
function interceptArray(name, dim, scope, callback) {
  let closure;
  Object.defineProperty(scope, name, {
    get() { return closure; },
    set(val) {
      if (Array.isArray(val) && val.length == dim) {
        closure = new Proxy(val, arrayChangeHandler(callback));
        callback(val);
      } else {
        throw new Error(`must be array with length=${dim} !`);
      }
    },
  });
}

// listen to obj[property] assigment
function objChangeHandler(callback, mapping) {
  return {
    get(target, name) {
      return name in target ? target[name] : undefined;
    },
    set(target, property, value, receiver) {
      target[property] = value;
      callback(mapping.map((p) => target[p]));
      return true;
    },
    deleteProperty(target, property) {
      return false;
    },
  };
}

// listen to obj={} assigment
function interceptObj(name, scope, callback, mapping = []) {
  let closure;
  Object.defineProperty(scope, name, {
    get() { return closure; },
    set(val) {
      if (val instanceof Object && eqSet(new Set(Object.keys(val)), new Set(mapping))) {
        closure = new Proxy(val, objChangeHandler(callback, mapping));
        callback(mapping.map((p) => val[p]));
      } else {
        throw new TypeError('mapping is not match with object !');
      }
    },
  });
}

// listen to vec[property] assigment
function vectorChangeHandler(callback, mapping) {
  return {
    get(target, name) {
      return name in target ? target[name] : undefined;
    },
    set(target, property, value, receiver) {
      target[property] = value;
      callback(mapping.map((p) => target[p]));
      return true;
    },
    deleteProperty(target, property) {
      return false;
    },
  };
}

// listen to =vec() assigment
function interceptVector(name, scope, callback, mapping = []) {
  let closure;
  Object.defineProperty(scope, name, {
    get() { return closure; },
    set(val) {
      if (val instanceof vector) {
        closure = new Proxy(val, vectorChangeHandler(callback, mapping));
        callback(mapping.map((p) => val[p]));
      } else {
        throw new TypeError('must be vec !');
      }
    },
  });
}

// listen to = assigment
function interceptValue(name, scope, callback) {
  let closure;
  Object.defineProperty(scope, name, {
    get() { return closure; },
    set(val) {
      closure = val;
      callback([val]);
    },
  });
}

function intercept(variable, scope, callback) {
  const { type } = variable;
  const { dim } = variable;
  const { name } = variable;

  if (type === 'vector') {
    if (dim != 3) throw new RangeError('dim must be 3 if type is vector !');
    interceptVector(name, scope, callback, ['x', 'y', 'z']);
  } else if (type === 'array') {
    if (dim <= 0) throw new RangeError('dim must be >0 if type is array !');
    interceptArray(name, dim, scope, callback);
  } else if (type === 'value') {
    if (dim != 1) throw new RangeError('dim must be 1 if type is value !');
    interceptValue(name, scope, callback);
  } else {
    throw new Error('type must be one of vector, array, or value !');
  }
}
