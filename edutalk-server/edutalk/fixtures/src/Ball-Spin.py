
display(width = 700, height = 700, background = vec(1, 1, 1),center = vec(0, 0.25, 0), range = 1.5, forward = vec(0, -0.8, -1))
init_value_box = label(pos=vec(-0.45, 1.40, 0), text = 'Initial values:\nFriction:\nSpeed:', height = 25, border = 15, font = 'monospace', color = color.black)
ball_spd_box = label(pos=vec(0.45, 1.40, 0), text = 'Speed:', height = 25, border = 15, font = 'monospace', color = color.black) 
count = 0
ball = sphere(radius = 0.35, pos = vec(0, 0.35, 0.1), texture=dict(file=textures.earth, bumpmap=bumpmaps.stucco))
is_running = False
Speed = 0
friction = 0.5

def action(data):
    global count, ball, is_running, previous_speed, Speed, a, friction, new_data
    new_data = data[0]
    dt = 0.001
    g = 9.8
    m = 0.5
    fric_coef = friction
    console.log("friction:"+friction)
    s = 0.01 
    ball_inertia = 2 * m * 0.35 ** 2 / 3 
    torque = fric_coef * m * g * s 
    a = 0
    count = 0
    speed = new_data
    if speed > 0:
        a = -torque / ball_inertia
    if speed < 0:
        a = torque / ball_inertia
    previous_speed = speed 

    def step():
        global Speed, dt, a, count, previous_speed, is_running, init_value_box, ball_spd_box, friction, count, new_data
        speed += a * dt 
        init_value_box.text = 'Initial values:\nFriction:' + friction.toFixed(2) + '\nSpeed: ' + str(round(new_data, 1))
        delta_angle = speed * dt + 0.5 * a * dt ** 2
        ball.rotate(angle = delta_angle, axis = vec(0,1,0))
        if count % 1000 == 0:
            ball_spd_box.text = 'Speed:' + str(round(speed, 1))
        if previous_speed * speed <= 0 or speed == 0:
            is_running = False
            return
        else:
            rate(1000,step)
        previous_speed = speed

    if is_running == False:
        is_running = True
        step()

def Speed(data):
    global is_running
    if data != None:
        new_data = data[0] 
        action([new_data])

def Friction(data):
    if data != None:
        global friction
        friction = data[0]


def setup():
    profile = {
        'dm_name': 'Ball-Spin',
        'df_list': [Speed,Friction]
    }
    dai(profile)

setup()
