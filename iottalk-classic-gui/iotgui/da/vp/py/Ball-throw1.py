g = vector(0, -9.8, 0)
dt = 0.005
is_running = False
speed = 0
angle = 45 * Math.PI / 180
height = 40


def axis_init():
    x_start = 0
    x_end = 500
    x_grid_num = 20
    x_label_num = 6

    y_start = 0
    y_end = 200
    y_grid_num = 10
    y_label_num = 6

    arrow(pos=vec(x_start, y_start, 0),
          axis=vec(x_end + (x_end - x_start) / 10, 0, 0),
          shaftwidth=1,
          color=color.white)

    arrow(pos=vec(x_start, y_start, 0),
          axis=vec(0, y_end + (y_end - y_start) / 10, 0),
          shaftwidth=1,
          color=color.white)

    for i in range(x_grid_num):
        box(pos=vec(x_start + (i + 1) * (x_end / x_grid_num),
                    (y_start + y_end) / 2,
                    0),
            height=y_end)

    for i in range(y_grid_num):
        box(pos=vec((x_start + x_end) / 2,
                    y_start + (i + 1) * (y_end / y_grid_num),
                    0),
            length=x_end)

    for i in range(x_label_num):
        label(pos=vec(x_start + x_end * i / (x_label_num - 1),
                      y_start - 20,
                      0),
              text=str(x_end * i / (x_label_num - 1)),
              font='monospace',
              box=False)

    for i in range(y_label_num):
        label(pos=vec(x_start - 20,
                      y_start + y_end * i / (y_label_num - 1),
                      0),
              text=str(y_start + y_end * i / (y_label_num - 1)),
              font='monospace',
              box=False)


def projectile_init():
    global init_value_box, ball_pos_box
    display(width=800,
            height=600,
            forward=vec(0.5, -0.05, -1),
            background=vec(0.6, 0.3, 0.2),
            center=vec(200, 100, 0),
            range=250)

    box(length=500,
        height=0.5,
        width=250,
        pos=vec(250, 0, 0),
        color=vec(0, 1, 0))

    ball_pos_box = label(pos=vec(400, 300, 0),
                         text='Position:\nX:\nY:\nZ:',
                         height=20,
                         border=10,
                         font='monospace',
                         color=color.white)

    init_value_box = label(pos=vec(200, 300, 0),
                           text='Initial values:\nAngle:\nHeight:\nSpeed:',
                           height=20,
                           border=10,
                           font='monospace',
                           color=color.white)
    axis_init()


def projectile_motion(data):
    global is_running, ball_pos_box, ball_touch, height, angle
    speed = data
    ball = sphere(pos=vec(0, height, 0), radius=8, color=color.white)
    ball.velocity = vector(speed * cos(angle), speed * sin(angle), 0)

    ball_touch = 0
    frame_count = 0

    def jump():
        global g, dt, is_running, frame_count, isExist, ball_touch
        ball.pos = ball.pos + ball.velocity * dt + 0.5 * g * (dt ** 2)

        if ball.pos.y < 8 and ball.velocity.y < 0:
            ball.velocity.y = - ball.velocity.y
            ball_touch += 1
        else:
            ball.velocity = ball.velocity + g * dt

        if ball.pos.x > 500 or ball_touch >= 10:
            ball.visible = False
            is_running = False
            return
        else:
            rate(1 / dt, jump)

        if frame_count % 10 == 0:
            ball_pos_box.text = ('Position:\n' +
                                 'X:' + str(round(ball.pos.x, 1)) + '\n' +
                                 'Y:' + str(round(ball.pos.y, 1)) + '\n' +
                                 'Z:' + str(ball.pos.z))
        frame_count += 1

    jump()


def Angle_O(data):
    if data is not None:
        global angle
        angle = data[0] * Math.PI / 180
        update()


def Speed_O(data):
    console.log(data)
    if not is_running and (data is not None):
        global is_running, speed
        speed = data[0]
        is_running = True
        update()
        projectile_motion(speed)


def Height_O(data):
    if data is not None:
        global height
        height = data[0]
        update()


def setup():
    projectile_init()
    profile = {
        'deviceModel': 'Ball-throw1',
        'idfList': [],
        'odfList': [[Angle_O, ['degree']], [Speed_O, ['m/s']], [Height_O, ['cm']]]
    }

    dai(profile)


def update():
    global init_value_box, height, angle, speed
    init_value_box.text = ('Initial values:\n' +
                           'Angle:' + round(angle * 180 / Math.PI, 1) + '\n' +
                           'Height:' + str(round(height, 1)) + '\n' +
                           'Speed:' + str(round(speed, 1)))

setup()
