# 物理參數區
ball_radius = 0.8 # 球半徑(m)
height = 15.0     # 初始高度(m)
_g = 9.8          # 重力加速度(m/s**2)
restitution = 0.7 # 恢復係數
# 模擬實驗參數區
freq = 240        # 更新頻率(Hz)
dt = 1.0 / freq   # 更新間隔(second)
duration = 10     # 演示時間(second)
updates = duration*freq # 總更新次數
cnt = 0                 # 還需要再更新幾次



def scene_init():
    #initial scene 
    global scene, ball, floor, height, ball_radius, label_gravity
    scene = display(width=800, height=700, center = vector(0, height/2, 0), background=vector(0.5, 0.5, 0))
    label_gravity = label( pos=vec(10,20,0), text='gravity: {:.1f}'.format(_g))
    floor = box(length=30, height=0.01, width=10, texture=textures.wood)
    ball = sphere(
        pos = vec(0, height, 0), 
        radius = ball_radius, 
        color = color.red
    )

def action(data):
    global cnt

    ##### 實驗一修改起始 #####
    # LOCK: 如果先前的實驗尚未結束(cnt > 0)，就不進行。
    if cnt > 0:
        return
    # LOCK: 如果重力加速度被設為0，就不進行。
    if data == 0:
        return
    # 重設倒數，模擬 updates 次
    #cnt = cnt / 0
    ##### 實驗一修改截止 #####
    
    # 設定重力加速度
    g = data
    label_gravity.text = 'gravity: {:.1f}'.format(_g)
    
    # 重設球的資訊，速度歸零，顏色設定為綠色代表模擬進行中。
    ball.visible = True
    ball.pos = vector(0, height, 0)
    ball.velocity = vector(0,0,0)
    ball.color = color.green
    
    # 計算下一個時間點的資料並將改變畫出
    def step():
        global cnt
        # 球的位置變化量是 速度 乘上 時間
        ball.pos = ball.pos + ball.velocity * dt
        
        ##### 實驗二修改起始 #####
        # 判斷球的新位置是否高於地面
        if ball.pos.y > ball_radius:
            # 如是，依重力加速度修改速度
            ball.velocity.y = ball.velocity.y - g*dt
        else:
            # 如否，依恢復係數計算出反彈後速度，並設定球的位置在地面上
            ball.velocity.y = -ball.velocity.y * restitution
            ball.pos.y = ball_radius
            if ball.velocity.y ** 2 < 0.01 * g:
                cnt = 0
        if ball.velocity.y > 0:
            ball.color = color.blue
        else:
            ball.color = color.green
        ##### 實驗二修改截止 #####
        
        # 倒數至零為止之前，都要模擬
        if cnt > 0:
            cnt -= 1
            rate(freq, step)
        else:
            # 倒數歸零之後，則把球改成紅色，代表模擬結束
            ball.color = color.red
        
    step()
	
### 請勿修改以下程式碼 ###
def Gravity(data):
    global _g
    if data != None:
        _g = data[0]
        action(_g)

def setup():
    #global ball
    scene_init()
    profile = {
        'dm_name' : 'Free_Fall2',
        'df_list' : [Gravity],
    }	
    dai(profile)

setup()
