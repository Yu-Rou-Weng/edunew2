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
# 以上變數與actuators連接
# 請勿修改上方程式碼

freq = 120        # 更新頻率(Hz)
g = 9.8
m = 1.0
s = 0.1
ball_inertia = 2 * m * 0.35 ** 2 / 3
dt = 1 / freq

# 初始化場景
def scene_init():
    global scene, init_value_box, ball_spd_box, ball, is_running
    # 設定場景寬、高、中心位置及顏色
    scene = display(width = 700, height = 700, background = vec(1, 1, 1),center = vec(0, 0.25, 0), range = 1.5, forward = vec(0, -0.8, -1))
    # 設定標語位置、內容、高度、字體及顏色
    init_value_box = label(pos=vec(-0.35, 1.40, 0), text = '', height = 25, border = 15, font = 'monospace', color = color.black)
    ball_spd_box = label(pos=vec(0.55, 1.40, 0), text = 'Speed_I:', height = 25, border = 15, font = 'monospace', color = color.black)
    # 設定球的半徑、位置及貼在球上的圖
    ball = sphere(radius = 0.35, pos = vec(0, 0.35, 0.1), texture={'file':textures.earth, 'bumpmap':bumpmaps.stucco})

# 每秒鐘更新顯示數據
def update_init():
    global init_value_box
    {% set label_text = {'cont':'Initial values:\\nFriction_I: {:.2f}\\nSpeed_I: {:.2f}'} %}
    {%- set value_list = [] -%}
    {%- for df_name, _ in odf_list -%}
        {%- if df_name != 'Friction_I' and df_name != 'Speed_I'-%}
            {%- if "_O" in df_name -%}
                {%- set df_name = df_name[:-2].lower() -%}
                {%- if df_name == "humidity" or df_name == "uv" or df_name == "alcohol" -%}
                    {%- if value_list.append(df_name) -%}
                    {%- endif -%}
                    {%- set tmp = df_name+': {:.2f}\\n' -%}
                {%- else -%}
                    {%- if value_list.append(df_name+'.x') -%}
                    {%- endif -%}
                    {%- if value_list.append(df_name+'.y') -%}
                    {%- endif -%}
                    {%- if value_list.append(df_name+'.z') -%}
                    {%- endif -%}
                    {%- set tmp = df_name+': {:.2f} {:.2f} {:.2f}\\n' -%}
                {%- endif -%}
            {%- else -%}
            {%- set df_name = df_name.lower() -%}
                {%- if value_list.append(df_name) -%}
                {%- endif -%}
                {%- set tmp = df_name+': {:.2f}\\n' -%}
            {%- endif -%}
            {%- if label_text.update({'cont':label_text.cont+tmp}) -%}
            {%- endif -%}
        {%- endif -%}
    {%- endfor -%}
    init_value_box.text='{{label_text.cont}}'.format(Friction_I, Speed_I, {{value_list | join(',')}})

def update_info():
    global ball_spd_box, current_speed
    ball_spd_box.text = 'Speed: {:.2f}'.format(current_speed, 1)

# 重設各項參數
def reset():
    global prev_state, current_speed, torque, a
    update_init()
    # 將現有(速度、摩擦力係數)數值存至prev_state中
    prev_state = ({{odf_list|e|replace("&#39;", "")|replace("_O","")|lower()}}) # FIXME
    current_speed = Speed
    # 計算摩擦力
    torque = Friction_I * m * g * s
    if Speed_I > 0:
        a = -torque / ball_inertia
    elif Speed_I < 0:
        a = torque / ball_inertia
    else:
        a = 0

scene_init()
reset()

cnt = 0
while True:
    # 等待(1.0/freq)秒
    rate(freq)
    # 檢查現有(速度、摩擦力係數)數值不等於prev_state中的數值是否相同
    # 即檢查是否有新的速度或新的摩擦力係數傳入
    if prev_state != ({{odf_list|e|replace("&#39;", "")|replace("_O","")|lower()}}):  #FIXME
        reset()
    # 用cnt記數使每(1.0/freq)*(freq//5) = 0.2秒更新資訊
    if cnt % (freq // 5) == 0:
        update_info()
    # 如果球現在速度不等於0，計算新的速度。等於0的話表示球已停下，不用計算
    if current_speed != 0:
        current_speed += a * dt
        delta_angle = current_speed * dt + 0.5 * a * dt ** 2
        ball.rotate(angle = delta_angle, axis = vec(0,1,0))
        # 如果算出來的速度是負的，表示球已停下，將球的速度設為0
        if current_speed * Speed <= 0:
            current_speed = 0

    cnt = cnt + 1
