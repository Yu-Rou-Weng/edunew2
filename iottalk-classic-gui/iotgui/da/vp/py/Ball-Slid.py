speed = 0
angle = 45 * Math.PI / 180
g = 9.8
friction = 0
dt = 0.001


def axis_init():
    a = 0
    b = 0
    c = 2
    d = 2
    arrow(pos=vec(a, b, 0),
          axis=vec(c + 0.2, 0, 0),
          shaftwidth=0.02)
    arrow(pos=vec(a, b, 0),
          axis=vec(0, d + 0.2, 0),
          shaftwidth=0.02)

    for t in range(0, 20):
        box(pos=vec(a + (t + 1) * (c / 20), b + d / 2, 0),
            length=0.01,
            height=d,
            width=0.01)

    for j in range(0, 10):
        box(pos=vec(a + c / 2, b + (j + 1) * (d / 10), 0),
            length=c,
            height=0.01,
            width=0.01)

    for x in range(0, 6):
        label(pos=vec(a + x * (c / 5), b - 2 * d / 20, 0),
              text=str(round(x * (c / 5) * 100) / 100),
              height=20,
              border=12,
              font='monospace',
              box=False)

    for y in range(0, 6):
        label(pos=vec(a - 2 * c / 40, b + y * (d / 5), 0),
              text=str(round(b + y * (d / 5) * 100) / 100),
              height=20,
              border=12,
              font='monospace',
              box=False)


def sliding_init():
    global init_value_box, spd_box, floor, ball
    display(width=1000,
            height=800,
            background=vec(0.6, 0.3, 0.2),
            center=vec(2.5, 1.0, 0),
            forward=vec(-1, -1, -3),
            range=2.6)

    init_value_box = label(
        pos=vec(4.0, 2.5, 0),
        text='Initial values:\nSpeed:\nAngle:\nGravity:\nFriction:',
        height=25,
        border=15,
        font='monospace'
    )
    spd_box = label(
        pos=vec(4.0, 1.5, 0),
        text='Speed in animation:\n',
        height=25,
        border=15,
        font='monospace'
    )
    floor = box(
        pos=vec(1 - 0.125 * cos(angle),
                2 - tan(angle) - 0.125 * cos(angle),
                0),
        axis=vec(-1 * cos(angle), 1 * sin(angle), 0),
        size=vec(2.1 / cos(angle), 0.05, 1),
        color=color.green
    )
    ball = sphere(
        pos=vec(0, 2, 0),
        radius=0.1)
    ball.visible = False

    axis_init()


def action():
    update()

    global ball, a
    ball.pos = vec(0, 2, 0)
    ball.visible = True
    ball.velocity = vec(1 * speed * cos(angle),
                        -1 * speed * sin(angle),
                        0.0)
    a = vector(g * sin(angle) * cos(angle) - friction * g * cos(angle) ** 2,
               -g * sin(angle) ** 2 + friction * g * sin(angle) * cos(angle),
               0)

    def step():
        global spd_box, a, ball
        ball.pos = ball.pos + ball.velocity * dt + 0.5 * a * dt ** 2
        ball.velocity = ball.velocity + a * dt

        if friction >= sin(angle) / cos(angle):
            return

        spd_box.text = 'Speed:\nx={:.2f}, y={:.2f}, z={:.2f}'.format(
            round(ball.velocity.x * 100) / 100,
            round(ball.velocity.y * 100) / 100,
            round(ball.velocity.z * 100) / 100)

        if ball.pos.x >= 2 or ball.pos.y <= 0 or not ball.visible:
            return
        else:
            rate(1000, step)

    step()


def Angle_O(data):
    global angle
    if data is not None:
        angle = data[0] * Math.PI / 180
        update()


def Speed_O(data):
    global speed
    if data is not None:
        speed = data[0]
        action()


def Gravity_O(data):
    global g
    if data is not None:
        g = data[0]
        update()


def Friction_O(data):
    global friction
    if data is not None:
        friction = data[0]
        update()


def update():
    global init_value_box, angle, speed, g, ball, floor, friction
    ball.visible = False
    init_value_box.text = ('Initial values:\n' +
                           'Speed: x=' +
                           round(1 * speed * sin(angle) * 100) / 100 +
                           ', y=' +
                           round(-1 * speed * cos(angle) * 100) / 100 +
                           ', z=0.00\n' +
                           'Angle:' +
                           round(angle * 180 / Math.PI * 100) / 100 + '\n' +
                           'Gravity:' + g.toFixed(1) + '\n' +
                           'Friction:' + friction.toFixed(1))

    if angle <= Math.PI / 4:
        floor.pos = vec(1 - 0.125 * sin(angle),
                        2 - tan(angle) - 0.125 * cos(angle),
                        0)
        floor.axis = vec(-1 * cos(angle), 1 * sin(angle), 0)
        floor.size = vec(2.1 / cos(angle), 0.05, 1)
    else:
        floor.pos = vec(1 / tan(angle) - 0.125 * sin(angle),
                        1 - 0.125 * cos(angle),
                        0)
        floor.axis = vec(-1 * cos(angle), 1 * sin(angle), 0)
        floor.size = vec(2.1 / sin(angle), 0.05, 1)


def setup():
    global ball
    sliding_init()
    profile = {
        'deviceModel': 'Ball-Slid',
        'idfList': [],
        'odfList': [[Angle_O, ['degree']],
                     [Speed_O, ['m/s']],
                     [Gravity_O, ['m/s^2']],
                     [Friction_O, ['unknow']]]
    }
    dai(profile)

setup()
