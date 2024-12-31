function UUID () {
  function s4() {
    return Math.floor((1 + Math.random()) * 0x10000)
      .toString(16)
      .substring(1);
  }
  return s4() + s4() + '-' + s4() + '-' + s4() + '-' +
         s4() + '-' + s4() + s4() + s4();
}

var dai = function (profile) {
  /*
  profile = {
    'dm_name': <DeviceModel name>,
    'idf_list': [ [<callback function with DeviceFeature name> , [<unit>, ...]], ...],
    'odf_list': [ [<callback function with DeviceFeature name> , [<unit>, ...]], ...],
    'onRegister': <callback function for register successly called>,
  }
  */
  if (!profile.name) {
      profile.name = profile.deviceModel + '_' + Math.floor(Math.random() * 100);
  }

  document.title = profile.name;
  parent.document.title = profile.name;

  $.get('/ec_endpoint')
    .done((data) => {
      profile.apiUrl = data.ec_endpoint;
      const da = new iottalkjs.DAI(profile);
      da.run();
    });
};

/*==Basic==*/
let project = window.location.hash.replace(/^#/,'');
let audio = {}

var preloadAudio = function(filename) {
  if (audio[filename] == undefined) {
    audio[filename] = new Audio('/da/vp/audio/' + filename);
  }
};

var playAudio = function(filename) {
  preloadAudio(filename);
  if (audio[filename] != undefined) {
    audio[filename].play();
  }
};

var execute = function (code) {
  let options = {
    lang: 'vpython',
    version: 2.1
  };

  try {
    let js_code = glowscript_compile(code, options);
    let program = eval(js_code);
    program(function(err){
      if (err) {
        // run error
        console.log(err);
      }
    });
  } catch (err) {
    // compile error
    console.log(err);
  }


};

var fetch_code = function(url){
  $.get(url)
   .done(function (data) {
     execute(data);
   })
   .fail(function (jqxhr, settings, execption) {
     console.log(execption);
  });
};

window.__context = {
  glowscript_container: $('#glowscript'),
};

var originHash;
$(function () {
  originHash = window.location.hash;
  fetch_code('/da/vp/py/'+ project + '.py');
});

$(window).on('hashchange', function (a) {
  if (window.location.hash != originHash) {
    window.location.hash = originHash;
  }
});
