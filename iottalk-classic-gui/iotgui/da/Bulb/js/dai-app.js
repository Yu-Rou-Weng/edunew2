$(function () {
    var r = 0;
    var g = 0;
    var b = 0;
    var lum = 0;

    function draw () {
        var rr = Math.floor((r * lum) / 100);
        var gg = Math.floor((g * lum) / 100);
        var bb = Math.floor((b * lum) / 100);
        $('.bulb-top, .bulb-middle-1, .bulb-middle-2, .bulb-middle-3, .bulb-bottom, .night').css(
            {'background': 'rgb('+ rr +', '+ gg +', '+ bb +')'}
        );
    }

    function Luminance (data) {
        lum = data[0]
        draw();
    }

    function Color_O (data) {
        r = data[0];
        g = data[1];
        b = data[2];
        draw();
    }

    function iot_app () {
        r = 40;
        g = 40;
        b = 40;
        lum = 100;
        draw();
    }

    var profile = {
        'dm_name': 'Bulb',
        'df_list': [Luminance, Color_O],
    }

    var ida = {
        'iot_app': iot_app,
    };

    dai(profile, ida);
});
