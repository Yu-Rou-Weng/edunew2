function ajaxJson(url, type, jsonData, cb, errorCallback) {
  return $.ajax({
    url,
    type,
    headers: { 'x-csrf-token': csrf.token },
    contentType: 'application/json',
    dataType: 'json',
    data: JSON.stringify(jsonData),
    success: cb,
    error: (jqXHR, textStatus, errorThrown) => {
      if (errorCallback !== undefined) errorCallback(jqXHR, textStatus, errorThrown);

      if (jqXHR.status === 0) return alert('Not connect.\n Verify Network.');
      if (jqXHR.status === 404) return alert('Requested page not found. [404]');
      if (jqXHR.status === 500) return alert('Unknown Error: Please try again later.');

      if (textStatus === 'parsererror') return alert('Requested JSON parse failed.');
      if (textStatus === 'timeout') return alert('Time out error.');
      if (textStatus === 'abort') return alert('Ajax request aborted.');

      if (jqXHR.responseJSON === undefined) return alert(jqXHR.responseText);
      if (jqXHR.responseJSON.reason.includes('CSRF')) {
        console.error(jqXHR.responseJSON.reason);
        return csrfRefresh().then(() => ajaxJson(url, type, jsonData, cb, errorCallback));
      }
      return console.error(jqXHR.responseJSON.reason);
    },
  });
}

function csrfRefresh() {
  return $.ajax({
    url: csrf.refreshUrl,
    type: 'GET',
    dataType: 'json',
    contentType: 'application/json',
    success(response) {
      csrf.token = response;
      console.log('CSRF token refreshed!');
    },
    error(jqXHR, textStatus, errorThrown) {
      console.error(jqXHR, textStatus, errorThrown);
      alert('Connection with server lost! Please refresh the page.');
    },
  });
}
