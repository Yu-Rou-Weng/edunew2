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

# 物理參數區
height = 15.0     # 初始高度(m)
restitution = 1.0 # 恢復係數

# 模擬實驗參數區
freq = 120        # 更新頻率(Hz)
dt = 1.0 / freq   # 更新間隔(second)

# 與流程控制有關參數
g = 5.0          # 定義初始重力加速度

# 初始化場景
def scene_init():
    # 初始場景、球、地板、文字方塊
    global scene, ball, floor, height, label_info
    scene = display(width=800, height=700, center = vec(0, height/2, 0), background=vec(0.5, 0.5, 0))
    floor = box(length=30, height=0.01, width=10, texture=textures.wood )
    ball = sphere(
        pos = vec(0, height, 0),
        radius = 0.5,
        color = color.green,
        velocity = vector(0,0,0),
        visible = True
    )
    label_info = label( pos=vec(10,20,0), text='', color = color.white)

scene_init()

while True:
    # 在每秒重畫 freq 次
    rate(freq)

    # 更新顯示數據
    {% set label_text = {'cont': ''} -%}
    {%- set value_list = [] -%}
    {% for iv in iv_list -%}
        {%- set _var = iv.giv_name ~ iv.index -%}
        {%- if iv.params | length == 1 -%}
            {%- if value_list.append(_var) -%}{%- endif -%}
            {%- set tmp = _var + ': {:.2f} \\n' -%}
        {%- else -%}
            {%- set t = {'cont': ''} -%}
            {%- if t.update({'cont': t.cont + _var + ': '}) -%}{%- endif -%}
            {%- for param in iv.params %}
                {%- if loop.index == 1 -%}
                    {%- if value_list.append(_var + '.x') -%}{%- endif -%}
                    {%- if t.update({'cont': t.cont + '{:.2f} '}) -%}{%- endif -%}
                {%- elif loop.index == 2 -%}
                    {%- if value_list.append(_var + '.y') -%}{%- endif -%}
                    {%- if t.update({'cont': t.cont + '{:.2f} '}) -%}{%- endif -%}
                {%- elif loop.index == 3 -%}
                    {%- if value_list.append(_var + '.z') -%}{%- endif -%}
                    {%- if t.update({'cont': t.cont + '{:.2f} '}) -%}{%- endif -%}
                {%- endif -%}
            {%- endfor -%}
            {%- set tmp = t.cont + '\\n' -%}
        {%- endif -%}
        {%- if label_text.update({'cont': label_text.cont + tmp}) -%}{%- endif -%}
    {% endfor -%}

    {%- if label_text.update({'cont':label_text.cont+ 'current_speed: {:.2f}\\nheight: {:.2f}\\n'}) -%}
    {%- endif -%}

    label_info.text='{{label_text.cont}}'.format({{value_list|join(',')}},abs(ball.velocity.y),ball.pos.y)

    # 更新球半徑、重力加速度
    ball.radius = Radius_I
    g = Gravity_I

    # 計算下一個時間點的資料並將改變畫出
    # 球的位置變化量是 速度 乘上 時間
    ball.pos = ball.pos + ball.velocity * dt
    # 判斷球的新位置是否高於地面
    if ball.pos.y > ball.radius:
        # 如是，依重力加速度修改速度
        ball.velocity.y = ball.velocity.y -g*dt
    else:
        # 如否，依恢復係數計算出反彈後速度，並設定球的位置在地面上
        ball.velocity.y = -ball.velocity.y * restitution
        ball.pos.y = ball.radius
