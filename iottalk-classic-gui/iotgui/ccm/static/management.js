var _is_init = false;
window.iottalk = {};

function anno_callback() {

}

function gui_init(){
    resize();

    // init data
    mqtt_client.request('get_tag_list', null, (data)=>{
        window.iottalk.tag_list = data;
    });
    mqtt_client.request('get_type_list', null, (data)=>{
        window.iottalk.type_list = data.type_list;
    });
    mqtt_client.request('get_unit_list', null, (data)=>{
        window.iottalk.unit_list = data;
    });

    if (_is_init) {
        $('#manage-feature').click();
        return;
    }

    _is_init = true;

    $(window).resize(resize);

    // bind event
    // nav
    $(document).on('click', '#manage-feature', show_feature_management);
    $(document).on('click', '#manage-model', show_model_management);

    //device feature
    $(document).on('click', '.type-radio', reload_feature_list);
    $(document).on('change', '#df-select', show_feature_info);
    $(document).on('change', '#dfc-select', change_feature_category);

    $(document).on('blur keyup mouseup', '#feature-params', change_parameter_number);
    $(document).on('click', '#feature-save', save_feature);
    $(document).on('click', '#feature-delete', delete_feature);
    $(document).on('change', '.feature-unit-select', select_unit);

    //device model
    $(document).on('change', '#dm-select', select_model);
    $(document).on('click', '.selected-df', show_model_feature_info);
    $(document).on('change', '.content-checkbox', select_model_feature);
    $(document).on('click', '#model-save', save_device_model);
    $(document).on('click', '#model-delete', delete_device_model);
    $(document).on('change', '.feature-type-select', save_model_feature_temp);
    $(document).on('change', '.feature-min-input', save_model_feature_temp);
    $(document).on('change', '.feature-max-input', save_model_feature_temp);
    $(document).on('change', '.feature-unit-select', save_model_feature_temp);

    $(document).on('change', '#dm-dfc-select', change_model_feature_category);

    $('#manage-feature').click();
}

function resize() {
    let window_height = window.innerHeight- $('nav').height() - 2;
    $('html').css('height', window_height);
    $('#left-window').css('height', window_height);
    $('#right-window').css('height', window_height);
}

function show_feature_management() {
    $('.active').removeClass('active');
    $(this).addClass('active');
    $('#feature-container').empty();
    $('#model-container').empty();

    function callback(data) {
        $('#feature-container').empty();
        $('#model-container').empty();
        window.iottalk.category = data;
        $('#feature-container').append(make_feature_management_html(data));
        $('.type-radio')[0].click();
    }
    mqtt_client.request('get_device_feature_category_list', {}, callback);
}

function reload_feature_list(event, df_id) {
    function callback(data) {
        let df_type = $('.type-radio:checked').val();
        $('#feature-list').empty();
        $('#feature-info').empty();
        $('#model-container').empty();
        $('#feature-list').append(make_feature_list_html(data, df_type));

        if (typeof df_id == 'number' || typeof df_id == 'string') {
            $('#df-select').val(df_id).trigger('change');
        }
        show_feature_info()
    }

    // When the user is adding a Feature,
    // switching the type does not clear the workspace.
    if ($('#df-select option:selected').val() == "-1" && !df_id)
        return;

    mqtt_client.request('get_device_feature_list', {}, callback);
}

function change_feature_category() {
    let df_type = $('.type-radio:checked').val();
    let category = $('#dfc-select').val();

    if (category == 'add new category') {
        //add new device feature category
        let new_dfc_name = "";
        while (true) {
            new_dfc_name = prompt("Please enter new category name: ");
            if (!new_dfc_name) {
                return;
            }
            else if (new_dfc_name == "add new category" || !new_dfc_name.trim()) {
                alert('invalid category name');
            }
            else {
                break;
            }
        }
        if ($('#dfc-select').find('option[value=' + new_dfc_name + ']').length) {
            // exist
            $('#dfc-select').val(new_dfc_name);
            $('#dfc-select').trigger('change');
        } else {
            // add new
            function callback(data) {
                let new_dfc_name = data.dfc_name;
                $('#dfc-select').append($('<option>', {'text': new_dfc_name, 'value': new_dfc_name}));
                $('#dfc-select').val(new_dfc_name);
                $('#dfc-select').trigger('change');
            }

            mqtt_client.request('create_device_feature_category',
                                {'dfc_name': new_dfc_name},
                                callback);
        }

    } else {
        //select device feature category
        $('#df-select option').each(function(index, option) {
            if (index < 2) {
                return; // alternate & add new always show
            }

            option = $(option);
            // show right type and category
            if (df_type == option.attr('df-type') &&
                (category == option.attr('category') || category == 'all')) {
                option.removeClass('disappear-flag');
                option.attr('disabled', false);
            } else {
                option.addClass('disappear-flag');
                option.attr('disabled', true);
            }
        });

        // if selected df not in sight, change to add new
        if ($('#df-select option:selected').hasClass('disappear-flag')) {
            $('#df-select').val(-1);
            $('#df-select').trigger('change');
        }
    }
}

function change_model_feature_category() {
    let category = $('#dm-dfc-select').val();
    $('.df-container').each(function(index, container) {
        container = $(container);
        if (category == container.attr('category') || category == 'all') {
            container.removeClass('disappear-flag');
        } else {
            container.addClass('disappear-flag');
        }
    })
}

function show_feature_info() {
    let df_name = $('#df-select option:selected').text();
    let df_id = $('#df-select option:selected').val();

    function callback(data) {
        $('#feature-info').empty();
        $('#model-container').empty();
        $('#feature-info').append(make_feature_info_html(data));
        $('#model-container').append(make_feature_comment_html(data));
        //TODO upload
    }

    if (df_id == -1) {
        $('#dfc-select').val('None');
        data = {
            'df_id': -1,
            'comment': '',
            'param_no': 1,
            'df_type': $('.type-radio:checked').val(),
            'df_parameter': [{
                'df_type': 'int',
                'min': 0,
                'max': 0,
                'unit_id': 1
            }]
        }
        callback(data);
    } else {
        mqtt_client.request('get_device_feature_info', {'df_id': df_id}, callback);
    }
}

function change_parameter_number(event) {
    if (event.type === 'keyup' && event.keyCode != 13) {
        return;
    }

    let parameter_numbers = $(this).val();
    if (parameter_numbers <= 0) {
        parameter_numbers = 1;
        $(this).val(1);
    }

    let current_row = $('.dfp-row');
    if (current_row.length > parameter_numbers) {
        for (i = 0; i < current_row.length - parameter_numbers; i++) {
            $(current_row[current_row.length - i - 1]).remove();
        }
    } else if (current_row.length < parameter_numbers) {
        for (i = 0; i < parameter_numbers - current_row.length; i++) {
            $('.feature-info-table').append($(current_row[current_row.length - 1]).clone());
        }
    }
}

function select_unit() {
    let unit_id = $(this).children('option:selected').attr('unit_id');
    if (unit_id != -1) {
        return;
    }

    let new_unit_name = "";
    while (true) {
        new_unit_name = prompt("Please enter new unit name: ");
        if (!new_unit_name) {
            return;
        }
        else if (new_unit_name == "add new unit" || !new_unit_name.trim()) {
            alert('invalid unit name');
        }
        else {
            break;
        }
    }
    mqtt_client.request('create_unit', {'unit_name': new_unit_name}, reload_unit);
}

function reload_unit(data) {
    function callback(data) {
        $('.feature-unit-select').each(function (index, selector) {
            let pre_id = $($(selector).find('option:selected')[0]).attr('unit_id');
            if (pre_id == -1) {
                pre_id = data['unit_id'];
            }
            $(selector).empty();
            data.forEach(function (unit) {
                if (unit.unit_id == pre_id){
                    $(selector).append($('<option>', { 'text': unit.unit_name, 'unit_id': unit.unit_id, 'selected': 'selected'}));
                }
                else {
                    $(selector).append($('<option>', { 'text': unit.unit_name, 'unit_id': unit.unit_id }));
                }
            });

            $(selector).append($('<option>', { 'text': 'add new unit', 'unit_id': -1}));
        });
    }
    mqtt_client.request('get_unit_list', null, callback);
}

function save_feature() {
    let pre_df_id = $(this).attr('df_id');
    let df_name = $('#df-select option:selected').text();
    let df_category = $('#df-select option:selected').attr('category');
    let df_id = -1;
    let new_df_name;

    // check df_category
    if (!df_category && $('#dfc-select').val() == 'all') {
        alert('Please select category.');
        return;
    }

    // set df_name
    while (true) {
        new_df_name = prompt("The Device Feature name: ", df_name);
        if (!new_df_name) {
            return;
        }

        if (!/^[-\d\w]+$/i.test(new_df_name) || new_df_name == "add new feature") {
            alert("Invalid name");
            continue;
        }

        if ($('#df-select option:contains(' + new_df_name + ')').map((i,e)=>{if($(e).text()==new_df_name){return e;}}).length) {
            let selector = $($('#df-select option:contains(' + new_df_name + ')').map((i,e)=>{if($(e).text()==new_df_name){return e;}})[0]);
            if (selector.text() != new_df_name) {
                break;
            }
            df_id = selector.val();
            if (pre_df_id == df_id) {
                break;
            }
            if (!confirm('The Device Feature name exists.\nDo you want to replace it?')){
                df_id = -1;
                continue;
            }
        }
        break;
    }

    let data = {
        'df_name': new_df_name,
        'df_type': $('.type-radio:checked').val(),
        'comment': $('.feature-comment').val(),
        'df_category': $('#dfc-select').val(),
        'df_parameter': []
    };



    for (i = 0; i < $('#feature-params').val(); i++) {
        let param = {
            'param_type': $($('.feature-type-select option:selected')[i]).text(),
            'min': $($('.feature-min-input')[i]).val(),
            'max': $($('.feature-max-input')[i]).val(),
            'unit_id': $($('.feature-unit-select option:selected')[i]).attr('unit_id')
        };
        data.df_parameter.push(param);
    }

    function callback(data) {
        reload_feature_list(null, data['df_id']);
    }

    if (df_id == -1) {
        mqtt_client.request('create_device_feature', data, callback);
    } else {
        data.df_id = df_id
        mqtt_client.request('update_device_feature', data, callback);
    }
    
    show_save_gif("#feature-save");
}

function delete_feature() {
    if (!confirm('Are you sure to delete this Device Feature?')) {
        return;
    }

    function callback(data) {
        if (data.df_id) {
            reload_feature_list();
        } else {
            alert('This Device Feature is already in use.');
        }
    }

    mqtt_client.request('delete_device_feature', {'df_id': $(this).attr('df_id')}, callback);
}

function show_model_management(event, dm_id) {
    $('.active').removeClass('active');
    $('#manage-model').addClass('active');
    $('#feature-container').empty();
    $('#model-container').empty();

    function callback(data) {
        $('#model-container').append(make_model_management_html(data.dm_list));

        function feature_setting_callback(data2) {
            window.iottalk.df_list = data2;

            if (typeof dm_id == 'number' || typeof dm_id == 'string') {
                $('#dm-select').val(dm_id).trigger('change');
            }
            select_model();
        }
        mqtt_client.request('get_device_feature_list', {}, feature_setting_callback);
    }
    mqtt_client.request('get_device_model_list', {}, callback);
}

function select_model() {
    let dm_id = $('#dm-select option:selected').val();
    if (dm_id == -1) {
        data = {
            'dm_id': -1,
            'dm_name': 'add new model',
            'df_list': []
        }
        show_model_info(data);
    } else {
        mqtt_client.request('get_device_model_info', {'dm_id': dm_id}, show_model_info);
    }
}

function show_model_info(data) {
    window.iottalk.dm_info = data;

    $('#feature-container').empty();
    $('#model-info').empty();
    $('#model-info').append(make_model_info_html(data,
                                                 window.iottalk.df_list,
                                                 window.iottalk.category,
                                                 window.iottalk.tag_list));
}

function show_model_feature_info() {
    $('#feature-container').empty();
    let df_id = $(this).attr('df_id');
    window.iottalk.dm_info.df_list.forEach(function (df_info, index) {
        if (df_id.toString() === df_info.df_id.toString()) {
            $('#feature-container').append(make_model_feature_info_html(df_info));
        }
    })

    let selector = $('input[df_id=' + df_id + ']');
    selector.parents('.model-df-list-container').scrollTop(selector[0].offsetTop - 5);
}

function select_model_feature() {
    $('#feature-container').empty();
    let df_id = $(this).attr('df_id');
    let dm_info = window.iottalk.dm_info;
    if ($(this).is(':checked')) {
        //add df
        function callback(data) {
            dm_info.df_list.push(data);
            show_model_info(dm_info);
            $('.selected-df[df_id=' + df_id + ']').click();
        }

        mqtt_client.request('get_device_feature_info', {'df_id': df_id}, callback);
    } else {
        //remove df
        dm_info.df_list.forEach(function (df_info, index) {
            if (df_id.toString() === df_info.df_id.toString()) {
                dm_info.df_list.splice(index, 1);
            }
        })
        show_model_info(dm_info);
    }
}

function save_model_feature_temp() {
    if (!$('#dm-select')[0]) {
        return;
    }

    let df_id = $('#df-select').val();
    let dm_info = window.iottalk.dm_info;

    dm_info.df_list.forEach(function (df_info, index) {
        if (df_id.toString() === df_info.df_id.toString()) {
            $('.feature-type-select option:selected').each(function (index) {
                df_info.df_parameter[index].param_type = $(this).text();
            });
            $('.feature-min-input').each(function (index) {
                df_info.df_parameter[index].min = $(this).val();
            });
            $('.feature-max-input').each(function (index) {
                df_info.df_parameter[index].max = $(this).val();
            });
            $('.feature-unit-select option:selected').each(function (index) {
                df_info.df_parameter[index].unit_id = $(this).attr('unit_id');
            });;
        }
    })
    window.iottalk.dm_info = dm_info;
}

function save_device_model() {
    let pre_dm_id = $(this).attr('dm_id');
    let dm_name = $('#dm-select option:selected').text();
    let dm_id = -1;
    let new_dm_name;
    while (true) {
        new_dm_name = prompt("The Device Model name: ", dm_name);
        if (!new_dm_name) {
            return;
        }

        if (!/^[-\d\w]+$/i.test(new_dm_name) || new_dm_name == "add new feature") {
            alert("Invalid name");
            continue;
        }

        // check df_name
        if ($('#dm-select option:contains(' + new_dm_name + ')').map((i,e)=>{if($(e).text()==new_dm_name){return e;}}).length) {
            dm_id = $('#dm-select option:contains(' + new_dm_name + ')').map((i,e)=>{if($(e).text()==new_dm_name){return e;}}).val();
            // if not create new model, only allow the same name
            if (pre_dm_id == dm_id) {
                break;
            }
            if (!confirm('The Device Model name exists.\nDo you want to replace it?')){
                dm_id = -1;
                continue;
            }
        }
        break;
    }

    function callback(data) {
        show_model_management(null, data['dm_id']);
    }

    let dm_info = window.iottalk.dm_info;
    dm_info.dm_name = new_dm_name;
    dm_info.plural = $('#plural').is(':checked');
    dm_info.device_only = $('#device_only').is(':checked')

    // update tag
    dm_info.df_list.forEach(function (df, index){
        df.tags = [];
        let tag_id = $('.selected-df[df_id=' + df.df_id + '] select').val();
        if (Number(tag_id)) {
            df.tags.push({'tag_id': tag_id});
        }
    })

    // create or update
    if (dm_id == -1) {
        delete dm_info.dm_id;
        mqtt_client.request('create_device_model', dm_info, callback);
    } else {
        mqtt_client.request('update_device_model', dm_info, callback);
    }
}

function delete_device_model() {
    if (!confirm('Are you sure to delete this Device Model?')) {
        return;
    }

    function callback(data) {
        if (data.dm_id) {
            show_model_management();
        } else {
            alert('This Device Feature is already in use.');
        }
    }

    mqtt_client.request('delete_device_model', {'dm_id': $(this).attr('dm_id')}, callback);
}

function show_save_gif (unit_name) {
    $('#save-gif').remove();

    let img = $('<img>', {
        'src': '/static/images/save.gif',
        'id': 'save-gif'
    });

    $(img).insertAfter(unit_name);
    $(img).fadeIn(300).delay(500).fadeOut(500);
}
