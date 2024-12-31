Gravity_I = 0

Speed_I = 0

# 以上變數讀取感測器後會自動更新
# 請勿修改上方程式碼

# 物理參數區
ball_radius = 0.8 # 球半徑(m)
height = 12.0     # 初始高度(m)
Speed_I = 25.0        # 初始速度
Gravity_I = 5.0          # 萬有引力常數
direction = vec(1,0,0) # 初始方向

# 模擬實驗參數區
freq = 120        # 更新頻率(Hz)
dt = 1.0 / freq   # 更新間隔(second)

# 事件旗標區
reset_flag = False

# 重置
def reset_ball():
    global ball, reset_flag
    # 復位
    ball.pos = vec(0, height, 0)
    # 速度歸零
    ball.velocity = Speed_I * norm(direction)
    # 洗去旗標
    reset_flag = False

# 初始化場景
def scene_init():
    global scene, ball, floor, height, ball_radius, label_gravity
    scene = display(width=800, height=700, center = vec(0, 0, 0), background=vec(0.5, 0.5, 0))
    label_gravity = label(pos=vec(0.8*height,0.8*height,0), text='Gravity_I: {:.3f}\nSpeed_I: {:.3f}'.format(Gravity_I, Speed_I))
    floor = sphere(
        pos = vec(0, 0, 0),
        radius = 2*ball_radius,
        velocity = vec(0, 0, 0),
        color = color.red
    )
    ball = sphere(
        pos = vec(0, height, 0),
        radius = ball_radius,
        velocity =Speed_I * norm(direction),
        color = color.green
    )
    scene.autoscale = False

scene_init()

#用來判斷萬有引力常數、速度是否改變
prev_state = (Gravity_I, Speed_I)
while True:
    rate(freq)
    label_gravity.text = 'Gravity_I: {:.3f}\nSpeed_I: {:.3f}'.format(Gravity_I, Speed_I)
    # 模擬天體運動
    if (ball.pos-floor.pos).mag > floor.radius+ball_radius and ball.pos.mag < height*2:
        ball.pos = ball.pos + ball.velocity * dt
    ball.velocity = ball.velocity - Gravity_I * norm(ball.pos - floor.pos) / (ball.pos - floor.pos).mag2
    #如果萬有引力常數、速度已改變，重置畫面
    if prev_state != (Gravity_I, Speed_I):
        reset_flag = True
    if reset_flag == True:
        reset_ball()
    prev_state = (Gravity_I, Speed_I)
