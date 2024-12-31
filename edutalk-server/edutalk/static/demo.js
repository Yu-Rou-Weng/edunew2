/* global vpIndex:false videoIndex:false ajaxJson:false */

// define animation related variables
const cyberDeviceUrl = vpIndex;
const videoIndexUrl = videoIndex;

$(() => {
  // Initialize
  if (cyberDeviceUrl !== '') {
    $('#device-iframe').attr('src', cyberDeviceUrl);
    $('#video-iframe').attr('src', videoIndexUrl);
  }
});

// bind shared m2 here
ajaxJson(
  urls.m2Bind(),
  'POST',
  {},
  () => console.log('m2 device bind success'),
  () => console.error('m2 device bind failed'),
);
