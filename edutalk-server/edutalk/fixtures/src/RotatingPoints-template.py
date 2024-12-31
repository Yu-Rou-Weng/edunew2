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
{{ _var['name'] }} = vec({{ _var['default'][0] }}, {{ _var['default'][1] }}, {{ _var['default'][2] }})
    {% elif _var['type']=='value' -%}
{{ _var['name'] }} = {{ _var['default'][0] }}
    {% else -%}
{{ _var['name'] }} = {{ _var['default'] }}
    {% endif %}
{% endfor -%}
{%- if output_variables| length > 0 -%}
# 以上變數與actuators連接
{%- endif %}
# 請勿修改上方程式碼

def initial():
    global N, p
    scene.width = scene.height = 600
    scene.background = color.white
    scene.range = 1.3
    N = int(Number_I)
    p = []
    last = vec(0,0,0)
    for i in range(N):
        next = last+0.1*vec.random()
        while mag(next) > 1: # if next is outside the sphere, try another random value
            next = last+0.1*vec.random()
        p.append({'pos':next, 'radius':0.002+0.04*random(), 'color':(vec(1,1,1)+vec.random())/2})
        last = next
    c = points(pos=p, size_units='world')
initial()

while True:
    rate(60)
    scene.forward = scene.forward.rotate(angle=-0.005, axis=vec(0,1,0))
    if N != int(Number_I):
        scene.delete()
        scene = canvas()
        initial()
