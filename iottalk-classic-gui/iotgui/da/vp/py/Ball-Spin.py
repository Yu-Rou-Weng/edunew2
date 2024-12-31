friction = 0.5
g = 9.8
m = 0.5
is_running = False
dt = 0.001
s = 0.01

def init():
    global init_value_box, ball_spd_box, ball
    display(width=700,
            height=700,
            background=vec(1, 1, 1),
            center=vec(0, 0.25, 0),
            range=1.5,
            forward=vec(0, -0.8, -1))
    init_value_box = label(pos=vec(-0.45, 1.40, 0),
                           text='Initial values:\nFriction:\nSpeed:',
                           height=25,
                           border=15,
                           font='monospace',
                           color=color.black)
    ball_spd_box = label(pos=vec(0.45, 1.40, 0),
                         text='Speed:',
                         height=25,
                         border=15,
                         font='monospace',
                         color=color.black)
    ball = sphere(radius=0.35,
                  pos=vec(0, 0.35, 0.1),
                  texture=dict(file=textures.earth, bumpmap=bumpmaps.stucco))

def action(data):
    global speed, previous_speed, a, count, is_running, m, init_value_box, g, s, friction
    if is_running:
        return

    speed = data
    previous_speed = speed
    ball_inertia = 2 * m * 0.35 ** 2 / 3
    torque = friction * m * g * s

    if speed > 0:
        a = -torque / ball_inertia
    if speed < 0:
        a = torque / ball_inertia

    count = 0
    init_value_box.text = ('Initial values:\n' +
                           'Friction:' + friction.toFixed(2) + '\n' +
                           'Speed: ' + str(round(speed, 1)))

    def step():
        global speed, previous_speed, a, count, is_running, dt, ball_spd_box
        speed += a * dt
        delta_angle = speed * dt + 0.5 * a * dt ** 2
        ball.rotate(angle=delta_angle, axis=vec(0, 1, 0))

        if count % (1 / dt) == 0:
            ball_spd_box.text = 'Speed:' + str(round(speed, 1))

        if previous_speed * speed <= 0 or speed == 0:
            is_running = False
            return
        else:
            rate(1 / dt, step)
            previous_speed = speed

    if not is_running:
        is_running = True
        step()


def Speed_O(data):
    global is_running
    if data is not None:
        action(data[0])


def Friction_O(data):
    if data is not None:
        global friction
        friction = data[0]


def setup():
    init()
    profile = {
        'deviceModel': 'Ball-Spin',
        'idfList': [],
        'odfList': [[Speed_O, ['m/s']], [Friction_O, ['unknown']]]
    }
    dai(profile)

setup()
