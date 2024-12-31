{%- for iv in iv_list -%}
    {%- set _var = iv.giv_name ~ iv.index -%}
    {%- if iv.params | length == 1 -%}
{{ _var }} = {{ iv.params[0].default | safe }}
    {%- elif iv.type == 'array' -%}
        {%- set value_list = [] -%}
        {%- for param in iv.params -%}
        {%- set v0 = param.default -%}
        {%- if value_list.append(v0) -%}{%- endif -%}
        {%- endfor -%}
{{ _var }} = {{ value_list | safe }}
    {%- elif iv.type == 'vector' -%}
        {%- set v0 = iv.params[0].default -%}
        {%- set v1 = iv.params[1].default -%}
        {%- set v2 = iv.params[2].default -%}
{{ _var }} = vec({{ v0 | safe }}, {{ v1 | safe }}, {{ v2 | safe }})
    {%- endif  %}
{% endfor -%}
# 以上變數讀取感測器後會自動更新

{% for _var in output_variables -%}
    {% if _var['type']=='vector' -%}
{{ _var['name'] }} = vec({{ _var['default'][0] | safe }}, {{ _var['default'][1] | safe }}, {{ _var['default'][2] | safe }})
    {% elif _var['type']=='value' -%}
{{ _var['name'] }} = {{ _var['default'][0] | safe }}
    {% else -%}
{{ _var['name'] }} = {{ _var['default'] | safe }}
    {% endif %}
{% endfor -%}
{%- if output_variables| length > 0 -%}
# 以上變數與actuators連接
{%- endif %}
# 請勿修改上方程式碼

freq = 120        # 更新頻率(Hz)

# 初始化場景
def scene_init():
    global label_info
    scene = display(width=800, height=700, center=vector(10, 15, 0), background=vector(0.5, 0.5, 0))
    label_info = label(pos=vec(10, 20, 0), text='')

# 每秒鐘更新顯示數據
def update_info():
    global label_info
    {% set label_text = {'cont': ''} -%}
    {%- set value_list = [] -%}
    {% for iv in iv_list -%}
        {%- set _var = iv.giv_name ~ iv.index -%}
        {%- if value_list.append(_var) -%}{%- endif -%}
        {%- set tmp = _var + ': {} \\n' -%}
        {%- if label_text.update({'cont': label_text.cont + tmp}) -%}{%- endif -%}
    {% endfor -%}

    label_info.text = '{{ label_text.cont }}'.format({{ value_list | join(',') }})

scene_init()

cnt = 0
while True:
    rate(freq)
    cnt = cnt + 1
    if cnt % (freq // 5) == 0:
        update_info()
