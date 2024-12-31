// switch
$(function () {
    $(document).on('click', '.toggle-button', function() {
        $(this).toggleClass('toggle-button-selected');
    	var self_id = $(this).attr('id');
        var clicked = $(this).hasClass('toggle-button-selected');
        push(self_id, clicked ? 1 : 0);
    });
});

// Knob
$(function () {
    // Init vars
    var knobs = $('.knob-container');
    var knobVal = [];
    knobVal.length = knobs.length;

    // Init knob appearance
    knobs.knobKnob({
        startDeg: -45,
        degRange: 270,
        initVal: 0.6,
        numColorbar: 31,
    });

    // Check knob val updated or not
    function knobChecker() {
        // Check update
        for(var i=0; i<knobs.length; ++i)
            if( knobVal[i] !== $(knobs[i]).val() ) {
                knobVal[i] = $(knobs[i]).val().toString();
                push($(knobs[i]).attr('role'), parseFloat(knobVal[i]));
            }
    }
    setInterval(knobChecker, 250);
});


// Shared function
function push (feature, data, callback) {
    $.ajax({
        'url': './' + feature,
        'method': 'POST',
        'contentType': 'application/json',
        'data': JSON.stringify(data),
    }).done(function (msg) {
        console.log('Successed: '+ msg);
        $('#message').text('Successed: '+ msg);
    }).fail(function (msg) {
        console.log('failed: '+ msg.status +','+ msg.responseText);
        $('#message').text('failed: '+ msg.status +','+ msg.responseText);
    }).always(function() {
        if(typeof callback === 'function')
            callback();
    });
}

$(function () {
    console.log('YA');
});
