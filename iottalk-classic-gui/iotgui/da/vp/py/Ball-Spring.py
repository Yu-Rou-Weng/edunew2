change_flag = True
g = 9.8
r = 0.5
spring_coef = 10
mass = 0.1
dt = 0.001


def axis_init():
    a = 0
    b = 0
    c = 1
    d = 2
    a = a - 0.5
    b = b - 1.25
    arrow(pos=vec(a, b, 0),
          axis=vec(c + 0.2, 0, 0),
          shaftwidth=0.015)
    arrow(
        pos=vec(a, b, 0),
        axis=vec(0, d + 0.2, 0),
        shaftwidth=0.015)

    for t in range(0, 5):
        box(pos=vec(a + (t + 1) * (4 / 20), b + d / 2, 0),
            length=0.005,
            height=d,
            width=0.01)

    for j in range(0, 10):
        box(pos=vec(a + c / 2, b + (j + 1) * (d / 10), 0),
            length=c,
            height=0.005,
            width=0.01)

    for x in range(0, 3):
        label(pos=vec(a + x * (c / 5) * 2, b - 2 * d / 20 + 0.1, 0),
              text=str(round(a + x * (c / 5) * 2 * 100) / 100),
              height=20,
              border=10,
              font='monospace',
              box=False)

    for y in range(0, 6):
        label(pos=vec(a - 2 * c / 40 - 0.1, b + y * (d / 5), 0),
              text=str(round(b + y * (d / 5) * 100) / 100 + 0.01),
              height=20,
              border=10,
              font='monospace',
              box=False)


def init():
    global ball, spring, init_value_box
    display(width=700,
            height=800,
            background=vec(0.6, 0.3, 0.2),
            center=vec(0, -r * 0.6, 0),
            range=1.5)
    box(length=0.8,
        height=0.005,
        width=0.8,
        color=color.green,
        pos=vec(0, 0.75, 0))

    ball = sphere(radius=0.05, color=color.white)
    ball.pos = vec(0, -2 * r + 0.75, 0)

    spring = helix(radius=0.02,
                   thickness=0.01,
                   centor=vec(0, 0, 0),
                   axis=vec(0, -1, 0),
                   pos=vec(0, 0.75, 0))

    init_value_box = label(pos=vec(-1.45, 1.2, 0),
                           text='Initial values:\nSpring_Constant:\n\nMass:',
                           height=20,
                           border=10,
                           font='monospace',
                           color=color.white,
                           xoffset=1)

    axis_init()


def action():
    def reset_ball():
        ball.pos0 = vec(0, -2 * r + 0.75, 0)
        ball.pos = vec(0, -2 * r + 0.75, 0)
        ball.v = vec(0, 0, 0)
        ball.a = vec(0, 0, 0)
        console.log(spring_coef, mass)
        init_value_box.text = ('Initial values:\n' +
                               'Spring_Constant:' +
                               str(round(spring_coef, 1)) +
                               '\nMass:' +
                               mass.toFixed(1))

    def step():
        global change_flag
        if change_flag:
            reset_ball()
            change_flag = False

        ball.a = vec(0,
                     (spring_coef * (ball.pos0.y - ball.pos.y) / mass) - g,
                     0)

        spring.axis = ball.pos - spring.pos
        ball.v = ball.v + ball.a * dt
        ball.pos = ball.pos + (ball.v) * dt
        rate(1 / dt, step)

    step()


def SpringConst_O(data):
    global change_flag, spring_coef
    if data is not None:
        change_flag = True
        spring_coef = data[0]


def Mass_O(data):
    global change_flag, mass
    if data is not None:
        change_flag = True
        mass = data[0]


def setup():
    global axis, labels
    init()

    profile = {
        'deviceModel': 'Ball-Spring',
        'idfList': [],
        'odfList': [[SpringConst_O, ['N/m']], [Mass_O, ['kg']]],
        'onRegister': action
    }
    dai(profile)

setup()
