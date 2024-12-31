###  BANANA
### I'm User a
axis = []
labels = []
_speed = 0
_angle = 45 * Math.PI/180
g = 9.8
fric_coef = 0

def axisInit():
    a = 0
    b = 0
    c = 2
    d = 2
    axis.append(arrow(
        pos=vec(a,b,0), 
        axis=vec(c+0.2,0,0), 
        shaftwidth= 0.02, 
        color = color.white
    ))
    axis.append(arrow(
        pos=vec(a,b,0), 
        axis=vec(0,d+0.2,0), 
        shaftwidth= 0.02, 
        color = color.white))
    
    for t in range(0,20):
        axis.append(box(
            pos=vec(a + (t+1)*(c/20),b+d/2,0), 
            length=0.01, 
            height=d, 
            width=0.01)
        )
    
    for j in range(0,10):
        axis.append(box(
            pos=vec(a + c/2,b + (j+1)*(d/10),0), 
            length=c, 
            height=0.01, 
            width=0.01,
            color=color.gray(0.8)
        ))
        
    for x in range(0,6):
        num = str(round(x*(c/5) * 100 ) / 100)
        labels.append(label(
            pos=vec(a + x*(c/5),b-2*d/20,0), 
            text = num, 
            height = 20, 
            border = 12, 
            font = 'monospace', 
            color = color.white, 
            box = False)
        )
    
    for y in range(0,6):
        num = str(round(b+y*(d/5)  * 100) /  100)
        labels.append(label(
            pos=vec(a-2*c/40,b + y*(d/5),0), 
            text = num, 
            height = 20, 
            border = 12, 
            font = 'monospace', 
            color = color.white, box = False)
        )
    
def sliding_init():
    global scene, init_value_box, spd_box, _floor, ball
    scene = display(
        width = 900, 
        height = 800, 
        background = vec(0,0.5,0.5),
        center = vec(2.5,1.0,0), 
        forward = vec(-1,-1,-3), 
        range = 2.6
    )
    init_value_box = label(
        pos = vec(3.7, 2.5,0), 
        text = 'Initial values:\n' + 'Speed:\n' + 'Angle:\n'+ 'Gravity:\n' + 'Friction:', 
        height = 25, 
        border = 15, 
        font = 'monospace', 
        color = color.white
    )
    spd_box = label(
        pos = vec(3.7, 1.5,0), 
        text = 'Speed in animation:\n', 
        height = 25, 
        border = 15, 
        font = 'monospace', 
        color = color.white
    )
    axisInit()
    _floor = box(
        pos = vec(1 - 0.125 * cos(_angle), 2 - tan(_angle) - 0.125 * cos(_angle), 0),	
        axis = vec(-1 * cos(_angle), 1 * sin(_angle), 0),
        size = vec(2.1 / cos(_angle), 0.05, 1),
        texture = textures.wood
    )
    ball = sphere(
        pos = vec(0, 2, 0), 
        radius = 0.1, 
        color = color.white
    )
    ball.visible = False
    
def action(_speed):
    #console.log('gogogo')
    global scene, init_value_box, spd_box, _floor, ball, _angle, _speed, g, a, fric_coef
    dt = 0.001
    ball.pos = vec(0, 2, 0)
    ball.visible = True

    if _angle <= Math.PI / 4:
        _floor.pos = vec(1 - 0.125 * cos(_angle), 2 - tan(_angle) - 0.125 * cos(_angle), 0)	
        _floor.axis = vec(-1 * cos(_angle), 1 * sin(_angle), 0)
        _floor.size = vec(2.1 / cos(_angle), 0.05, 1)
    else:
        _floor.pos = vec(1/tan(_angle) - 0.125 * sin(_angle), 1 - 0.125 * cos(_angle), 0)
        _floor.axis = vec(-1 * cos(_angle), 1 * sin(_angle), 0)
        _floor.size = vec(2.1 /sin(_angle), 0.05, 1)

    ball.velocity = vec( 1 * _speed * cos(_angle), -1 * _speed * sin(_angle), 0.0)
    a = vector(g * sin(_angle) * cos(_angle) - fric_coef * g * cos(_angle) ** 2,
               - g * sin(_angle) ** 2 + fric_coef * g * sin(_angle) * cos(_angle), 
               0)

    init_value_box.text = 'Initial values:\nSpeed: x={}, y={}, z={}\nAngle:{}\nGravity:{}\nFriction:{}'.format(
         round(ball.velocity.x * 100) / 100, 
         round(ball.velocity.y * 100) / 100, 
         round(ball.velocity.z * 100) / 100, 
         round(_angle*180/Math.PI *100) / 100, 
         g.toFixed(1), 
         fric_coef.toFixed(1))
    def step():
        if ball.velocity.x > 10:
            ball.color = color.cyan
        else:
            ball.color = color.white
        ball.pos = ball.pos + ball.velocity * dt + 0.5 * a * dt ** 2
        ball.visible = True
        ball.velocity = ball.velocity + a * dt
        if fric_coef >= sin(_angle)/cos(_angle):
            return
        #console.log("ball.velocity: "+ ball.velocity)
        spd_box.text = 'Speed:\nx={:.2f}, y={:.2f}, z={:.2f}'.format(
            round(ball.velocity.x * 100) / 100, 
            round(ball.velocity.y * 100) / 100, 
            round(ball.velocity.z * 100) / 100)
        if ball.pos.x >= 2 or ball.pos.y <= 0:
            return
        else:
            rate(1000, step)
    step()

def Angle(data):
    global _angle
    if data != None:
        _angle = data[0] * Math.PI / 180
        update()

def Speed(data):
    #console.log(data)
    global _speed
    if data != None:
        _speed = data[0]
        action(_speed)

def Gravity(data):
    global g
    if data != None:
        g = data[0]
        update()

def Friction(data):
    global fric_coef
    if data != None:
        fric_coef = data[0]
        update()

def update():
    global _angle, _speed, g, ball, _floor, fric_coef
    init_value_box.text = 'Initial values:\nSpeed: x={}, y={}, z={}\nAngle:{}\nGravity:{}\nFriction:{}'.format(
        round(1 * _speed * sin(_angle) * 100) / 100, 
        round(-1 * _speed * cos(_angle) * 100) / 100, 
        round(0.0) / 100, 
        round(_angle*180/Math.PI *100) / 100, 
        g.toFixed(1), 
        fric_coef.toFixed(1))

    if _angle <= Math.PI / 4:
        _floor.pos = vec(1 - 0.125 * sin(_angle), 2 - tan(_angle) - 0.125 * cos(_angle), 0)	
        _floor.axis = vec(-1 * cos(_angle), 1 * sin(_angle), 0)
        _floor.size = vec(2.1 / cos(_angle), 0.05, 1)
    else:
        _floor.pos = vec(1/tan(_angle) - 0.125 * sin(_angle), 1 - 0.125 * cos(_angle), 0)
        _floor.axis = vec(-1 * cos(_angle), 1 * sin(_angle), 0)
        _floor.size = vec(2.1 / sin(_angle), 0.05, 1)
    

    ball.visible = False

def setup():
    global ball
    sliding_init()
    profile = {
        'dm_name': 'Ball-Slid',
        'df_list': [Angle, Speed, Gravity, Friction]
    }
    dai(profile)

setup()
