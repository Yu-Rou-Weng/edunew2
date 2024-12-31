function make_feature_management_html(dfc_list) {
    let div_block = $('<div/>');
    let label_title = $('<label/>', {'class': 'management-title'}).text('Device Feature Window');
    div_block.append(label_title);

    // IDF or ODF radio button
    let div_content = $('<div/>', {'class': 'manage-content'});
    let div_type = $('<form/>', {'class': 'manage-info-container'});
    let type_title = $('<label/>', {'class': 'content-title'}).text('Type');

    let label_input = $('<label/>', {'class': 'type-label'});
    let radio_input = $('<input/>', {'type': 'radio', 'class': 'type-radio', 'name': 'df-type', 'value': 'input'});
    label_input.append(radio_input);
    let a_input = $('<a/>', {'class': 'type-a'}).text('IDF');
    label_input.append(a_input);

    let label_output = $('<label/>', {'class': 'type-label'});
    let radio_output = $('<input/>', {'type': 'radio', 'class': 'type-radio', 'name': 'df-type', 'value': 'output'});
    label_output.append(radio_output);
    let a_output = $('<a/>', {'class': 'type-a'}).text('ODF');
    label_output.append(a_output);

    let label_category = $('<label/>', {'class': 'content-title'}).text('Category');
    let select_category = $('<select>', {'id': 'dfc-select'});
    select_category.append($('<option>', {'text': 'all', 'value': 'all', 'selected': 'true'}));
    select_category.append($('<option>', {'text': 'add new category', 'value': 'add new category'}));
    dfc_list.forEach(function (dfc) {
        select_category.append($('<option>', {'text': dfc.dfc_name, 'value': dfc.dfc_name}));
    });

    div_type.append(type_title);
    div_type.append(label_input);
    div_type.append(label_output);
    div_type.append(label_category);
    div_type.append(select_category);

    div_content.append(div_type);
    div_content.append($('<div/>', {'id': 'feature-list', 'class': 'manage-info-container'}));
    div_content.append($('<div/>', {'id': 'feature-info'}));

    div_block.append(div_content);

    return div_block;
}

function make_feature_list_html(df_lists, df_type) {
    let div = $('<div/>');
    let list_title = $('<label/>', {'class': 'content-title'}).text('DF Name');
    let selected_new_flag = true;
    div.append(list_title);

    // select device feature list
    let df_select = $('<select/>', {'id': 'df-select'});
    if ('input' in df_lists) {
        df_lists['input'].forEach(function (df_info, index) {
            let df_option = $('<option>', {'text': df_info.df_name, 
                                           'value': df_info.df_id,
                                           'category': df_info.df_category,
                                           'df-type': 'input'});
            if ('input' != df_type){
                df_option.addClass('disappear-flag');
            } else if (selected_new_flag) {
                df_option.attr('selected', true);
                selected_new_flag = false;
            }
            df_select.append(df_option);
        });
    }
    if ('output' in df_lists) {
        df_lists['output'].forEach(function (df_info, index) {
            let df_option = $('<option>', {'text': df_info.df_name, 
                                           'value': df_info.df_id,
                                           'category': df_info.df_category,
                                           'df-type': 'output'});
            if ('output' != df_type){
                df_option.addClass('disappear-flag');
            } else if (selected_new_flag) {
                df_option.attr('selected', true);
                selected_new_flag = false;
            }
            df_select.append(df_option);
        });
    }
    df_select.prepend($('<option>', {'text': 'add new feature', 'value': -1, 'selected': selected_new_flag}));

    div.append(df_select);

    return div;
}

function make_feature_info_html(df_info) {
    let div = $('<div/>');

    //parameter numbers
    let div_params = $('<div/>', {'class': 'manage-info-container'});
    div_params.append($('<label/>', {'class': 'content-title'}).text('Number of parameters'));
    div_params.append($('<input/>', {'id': 'feature-params', 'type': 'number', 'min': 1}).val(df_info.df_parameter.length));


    //info table
    let table = $('<table/>', {'class': 'feature-info-table manage-info-container'});
    let table_title = $('<thead/>');
    table_title.append($('<td/>').text('Type'));
    table_title.append($('<td/>').text('Min'));
    table_title.append($('<td/>').text('Max'));
    table_title.append($('<td/>').text('Unit'));
    table.append(table_title);

    df_info.df_parameter.forEach(function (dfp, index) {
        let dfp_type_select = $('<select/>', {'class': 'feature-type-select'});
        window.iottalk.type_list.forEach(function (type, index) {
            let type_option = $('<option/>').text(type);
            if (type == dfp.param_type) {
                type_option.attr('selected', true);
            }
            dfp_type_select.append(type_option);
        });

        let dfp_min = $('<input/>', {'type': 'number', 'class': 'feature-min-input'}).val(dfp.min);
        let dfp_max = $('<input/>', {'type': 'number', 'class': 'feature-max-input'}).val(dfp.max);

        let dfp_unit_select = $('<select/>', {'class': 'feature-unit-select'});
        dfp_unit_select.append($('<option/>', {'unit_id': -1,}).text('add new unit'));
        window.iottalk.unit_list.forEach(function (unit, index) {
            let unit_option = $('<option/>', {'unit_id': unit.unit_id}).text(unit.unit_name);
            if (dfp.unit_id == unit.unit_id) {
                unit_option.attr('selected', true);
            }
            dfp_unit_select.append(unit_option);
        });

        let tr = $('<tr/>', {'class': 'dfp-row'});
        tr.append($('<td/>').append(dfp_type_select));
        tr.append($('<td/>').append(dfp_min));
        tr.append($('<td/>').append(dfp_max));
        tr.append($('<td/>').append(dfp_unit_select));

        table.append(tr);
    });

    //buttons
    let div_buttons = $('<div/>', {'class': 'manage-info-container'});
    div_buttons.append($('<button/>', {'id': 'feature-save', 'df_id': df_info.df_id}).text('Save'));
    if (df_info.df_id != -1) {
        div_buttons.append($('<button/>', {'id': 'feature-delete', 'df_id': df_info.df_id}).text('Delete'));
    }

    div.append(div_params);
    div.append(table);
    div.append(div_buttons);
    return div
}

function make_feature_comment_html(df_info) {
    let div_comment = $('<div/>', {'class': 'feature-comment-content'});
    div_comment.append($('<label/>', {'class': 'content-title'}).text('Description'));
    div_comment.append($('<br/>'));
    div_comment.append($('<textarea/>', {'class': 'feature-comment'}).val(df_info.comment));
    return div_comment;
}

function make_model_management_html(dm_list) {
    let div_block = $('<div/>', );
    let label_title = $('<label/>', {'class': 'management-title'}).text('Device Model Window');

    // select Device Model list
    let div_list = $('<div/>', {'id': 'model-list', 'class': 'manage-content'});
    let list_title = $('<label/>', {'class': 'content-title'}).text('DM Name');

    let dm_select = $('<select/>', {'id': 'dm-select'});
    dm_select.append($('<option>', {'text': 'add new model', 'value': -1}));
    dm_list.forEach(function (dm_info, index) {
        dm_select.append($('<option>', {'text': dm_info.dm_name, 'value': dm_info.dm_id}));
    });
    if (dm_select.children().length > 1) {
        dm_select.children()[1].setAttribute('selected', true);
    } else {
        dm_select.children()[0].setAttribute('selected', true);
    }

    div_list.append(list_title);
    div_list.append(dm_select);

    div_block.append(label_title);
    div_block.append(div_list);
    div_block.append($('<div/>', {'id': 'model-info', 'class': 'manage-content'}));
    return div_block;
}

function make_model_info_html(dm_info, df_list, category_list, tag_list) {
    let div = $('<div/>');

    // plural & device_only
    let div_dm_attr = $('<div/>');
    let plural_label = $('<label/>');
    let plural_checkbox = $('<input/>', {'type': 'checkbox', 'id': 'plural'});
    plural_checkbox.attr('checked', dm_info.plural);

    plural_label.append(plural_checkbox);
    plural_label.append('Generate DFO from feature number selector');
    div_dm_attr.append(plural_label);

    let device_only_label = $('<label/>');
    let device_only_checkbox = $('<input/>', {'type': 'checkbox', 'id': 'device_only'});
    device_only_checkbox.attr('checked', dm_info.device_only);

    device_only_label.append(device_only_checkbox);
    device_only_label.append('Generate DFO from registered device');
    div_dm_attr.append(device_only_label);

    //info
    let table_dm_info = $('<table/>', {'class': 'manage-info-container'});
    let table_dm_header = $('<thead/>');
    table_dm_header.append($('<td/>').text('Input Device Features'));
    table_dm_header.append($('<td/>').text('Output Device Features'));

    let table_dm_info_list = $('<tr/>');

    let div_dm_input_list = $('<div/>', {'class': 'model-df-list-container'});
    let div_dm_output_list = $('<div/>', {'class': 'model-df-list-container'});

    dm_info.df_list.forEach(function (df_info, index) {
        let df_container = $('<p/>', {'class': 'selected-df', 'df_id': df_info.df_id});
        df_container.append($('<label/>', {'class': 'none-bold-label'}).text(df_info.df_name));

        // Tag
        let select_tag = $('<select/>', {'class': 'selected-df-tag'});
        select_tag.append($('<option/>', {'value': null, 'text': 'No Tag'}));
        tag_list.forEach(function(tag, index) {
            select_tag.append($('<option/>', {'value': tag.tag_id, 'text': tag.tag_name}));
        })
        if (df_info.tags && df_info.tags.length) {
            select_tag.find('option[value=' + df_info.tags[0].tag_id + ']').attr('selected', true);
        }
        df_container.append(select_tag);


        if (df_info.df_type === 'input') {
            div_dm_input_list.append(df_container);
        } else {
            div_dm_output_list.append(df_container);
        }
    })

    table_dm_info_list.append($('<td/>').attr('valign', 'top').append(div_dm_input_list));
    table_dm_info_list.append($('<td/>').attr('valign', 'top').append(div_dm_output_list));

    table_dm_info.append(table_dm_header);
    table_dm_info.append(table_dm_info_list);

    //features title
    let div_category = $('<div/>', {'class': 'float-right'});
    let select_category = $('<select/>', {'id': 'dm-dfc-select', 'class': 'float-right'});
    select_category.append($('<option/>', {'value': 'all', 'text': 'all'}));
    category_list.forEach(function(category, index) {
        select_category.append($('<option/>', {'value': category.dfc_name, 'text': category.dfc_name}));
    })

    //features list
    let table_df_setting = $('<table/>', {'class': 'manage-info-container'});
    let table_df_header = $('<thead/>');
    table_df_header.append($('<td/>').text('Input Device Features'));
    table_df_header.append($('<td/>').text('Output Device Features'));

    let table_df_info_list = $('<tr/>');

    let div_df_input_list = $('<div/>', {'class': 'model-df-list-container'});
    let div_df_output_list = $('<div/>', {'class': 'model-df-list-container'});

    df_list.input.forEach(function (df_info, index) {
        let label = $('<label/>', {'class': 'none-bold-label'});
        let checkbox = $('<input/>', {'type': 'checkbox', 'class': 'content-checkbox', 'df_id': df_info.df_id});
        dm_info.df_list.forEach(function (dm_df_info, index) {
            if (dm_df_info.df_name === df_info.df_name) {
                checkbox.attr('checked', true);
            }
        })

        label.append(checkbox);
        label.append(df_info.df_name);
        let p = $('<p/>', {'class': 'df-container', 'category': df_info.df_category, 'df_id': df_info.df_id});
        p.append(label);
        div_df_input_list.append(p);
    })

    df_list.output.forEach(function (df_info, index) {
        let label = $('<label/>', {'class': 'none-bold-label'});
        let checkbox = $('<input/>', {'type': 'checkbox', 'class': 'content-checkbox', 'df_id': df_info.df_id});
        dm_info.df_list.forEach(function (dm_df_info, index) {
            if (dm_df_info.df_name === df_info.df_name) {
                checkbox.attr('checked', true);
            }
        })

        label.append(checkbox);
        label.append(df_info.df_name);
        let p = $('<p/>', {'class': 'df-container', 'category': df_info.df_category, 'df_id': df_info.df_id});
        p.append(label);
        div_df_output_list.append(p);
    })

    table_df_info_list.append($('<td/>').attr('valign', 'top').append(div_df_input_list));
    table_df_info_list.append($('<td/>').attr('valign', 'top').append(div_df_output_list));

    table_df_setting.append(table_df_header);
    table_df_setting.append(table_df_info_list);

    //buttons
    let div_buttons = $('<div/>', {'class': 'manage-info-container'});
    div_buttons.append($('<button/>', {'id': 'model-save', 'dm_id': dm_info.dm_id || -1}).text('Save'));
    if (dm_info.dm_id != -1 && dm_info.dm_id) {
        div_buttons.append($('<button/>', {'id': 'model-delete', 'dm_id': dm_info.dm_id}).text('Delete'));
    }

    div.append(div_dm_attr);
    div.append(table_dm_info);
    div.append($('<label/>').text('Add/Delete Device Feature'));
    div.append(select_category);
    div.append($('<label/>', {'class': 'float-right', 'text': 'Category'}));
    div.append(div_category);
    div.append(table_df_setting);
    div.append(div_buttons);
    return div;
}

function make_model_feature_info_html(df_info) {
    let div = make_feature_management_html([{'dfc_name':df_info.df_category, 'dfc_id': 0}]);
    div.find('input').attr('disabled', true);
    div.find(':radio[value="' + df_info.df_type  + '"]').attr('checked', true);
    div.find('#dfc-select').val(df_info.df_category);
    div.find('#dfc-select').attr('disabled', true);

    let list = make_feature_list_html({[df_info.df_type]: [df_info]}, df_info.df_type);
    list.find('#df-select').val(df_info.df_id);
    list.find('#df-select').attr('disabled', true);
    div.find('#feature-list').append(list);

    let info = make_feature_info_html(df_info);
    info.find('#feature-params').attr('disabled', true);
    info.find('#feature-save, #feature-delete').remove();
    info.find('.feature-unit-select option:contains("add new unit")').remove();
    div.find('#feature-info').append(info);

    return div;
}
