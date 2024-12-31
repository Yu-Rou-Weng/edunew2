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

N = 10

scene.title = f"{N} by {N} by {N} = {N*N*N} rotating cubes\n "
scene.caption = "Click a box to turn it white"

boxes = []

L = 6
scene.range = L
length = 0.6*L/N
height = 0.4*L/N

for x in range(N):
    for y in range(N):
        for z in range(N):
            b = box(color=vector(x/N,y/N,z/N),
                    pos=vector(L*(x/(N-1)-.5),L*(y/(N-1)-.5),L*(z/(N-1)-.5)),
                    size=vector(length,height,length))
            boxes.append(b)

scene.append_to_title("<div id='fps'/>")

lasthit = None
lastcolor = None

def handle_click():
    global lasthit, lastcolor
    if lasthit != None: lasthit.color = lastcolor
    hit = scene.mouse.pick
    if hit:
        lasthit = hit
        lastcolor = lasthit.color
        hit.color = color.white

scene.bind("mousedown", handle_click)

t = 0
dt = 0.01

while True:
    rate(200)
    for b in boxes:
        # Orientation_I.x ranging from 0 (inclusive) to 360 (exclusive).
        # Orientation_I.y ranging from -180 (inclusive) to 180 (exclusive).
        # Orientation_I.z ranging from -90 (inclusive) to 90 (exclusive).
        # we need to normalize these value
        b.color = vec(Orientation_I.x / 360, (Orientation_I.y + 180) / 360 , (Orientation_I.z + 90) / 180)
        b.rotate(angle=.01, axis=vector(0,1,0))
