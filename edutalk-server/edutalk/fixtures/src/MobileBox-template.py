{%- set excluded_list = ['Gravity','Gyroscope_O','Acceleration_O','Orientation_O']-%}
gravity = 5
def Gravity(data):
    global gravity
    if data != None:
        gravity = data[0]

acceleration = vec(0,0,0)
def Acceleration_O(data):
    global acceleration
    if data != None:
        acceleration.x = data[0][0]
        acceleration.y = data[0][1]
        acceleration.z = data[0][2]

gyroscope = vec(0,0,0)
def Gyroscope_O(data):
    global gyroscope
    if data != None:
        gyroscope.x = data[0][0]
        gyroscope.y = data[0][1]
        gyroscope.z = data[0][2]

orientation = vec(0,0,0)
def Orientation_O(data):
    global orientation
    if data != None:
        orientation.x = data[0][0]
        orientation.y = data[0][1]
        orientation.z = data[0][2]
{{ "\n" }}

{%-for df_name, _ in odf_list -%}
    {%- if df_name not in excluded_list -%}
        {%- if "_O" in df_name -%}
            {%- set sm_df = df_name -%}
            {%- set df_name = df_name[:-2].lower() -%}
            {%- if df_name == "humidity" or df_name == "uv" or df_name == "alcohol" -%}
{{df_name}} = 0
def {{sm_df}}(data):
    global {{df_name}}
    if data != None:
        {{df_name}} = data[0]
        {{ "\n" }}
            {%- else -%}
{{df_name}} = vec(0,0,0)
def {{sm_df}}(data):
    global {{df_name}}
    if data != None:
        {{df_name}}.x = data[0]
        {{df_name}}.y = data[1]
        {{df_name}}.z = data[2]
        {{ "\n" }}
            {%- endif -%}
        {%- else -%}
{{df_name.lower()}} = {{ df_means[df_name] }}
def {{df_name}}(data):
    global {{df_name.lower()}}
    if data != None:
        {{df_name.lower()}} = data[0]
        {{ "\n" }}
        {%- endif -%}
    {%- endif -%}
{%- endfor -%}

# 設定
def setup():
    profile = {
        'dm_name' : '{{ dm_name }}',
        'idf_list': [],
        'odf_list' : {{ odf_list | todf_list | safe }},
    }
    dai(profile)

setup()

{{ "\n" }}
# {{ odf_list | todf_list | safe }} 讀取感測器後會自動更新
# 請勿修改上方程式碼

freq = 120        # 更新頻率(Hz)

# 初始化場景
def scene_init():
    global label_info, a_box
    scene = display(width=800, height=700, center = vector(0, 0, 0), background=vector(0.5, 0.5, 0))
    label_info = label( pos=vec(3,4,0), text='')
    a_box = box(pos=vec(0,0,0),axis=vec(1,0,0),size=vec(10,3,1),color=color.red)

# 每秒鐘更新顯示數據
def update_info():
    global label_info
    {% set label_text = {'cont':'gravity: {:.2f}\\nacceleration: {:.2f} {:.2f} {:.2f}\\ngyroscope: {:.2f} {:.2f} {:.2f}\\norientation: {:.2f} {:.2f} {:.2f}\\n'} %}
    {%- set value_list = [] -%}
    {%- for df_name, _ in odf_list -%}
        {%- if df_name not in excluded_list -%}
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
    label_info.text='{{label_text.cont}}'.format(gravity,acceleration.x,acceleration.y,acceleration.z,gyroscope.x,gyroscope.y,gyroscope.z,orientation.x,orientation.y,orientation.z,{{value_list|join(',')}})

scene_init()

cnt = 0
while True:
    rate(freq)
    cnt = cnt + 1
    if cnt % (freq // 5) == 0:
        update_info()
    # 重力感測器有收到數值時，更新 a_box 的 axis
    if acceleration.mag > 0:
        a_box.axis = norm(acceleration)
