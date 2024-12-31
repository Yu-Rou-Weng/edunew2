ray_list = []
is_running = False


def init():
    global init_value_box
    display(background=vec(0.8, 0.8, 0.8),
            width=700,
            height=700,
            center=vec(0, 0, 5),
            fov=0.04)

    # draw arc, shapes.arc is not support in glowscript
    node_numbers = 20
    arcpath = [vec(Math.sin(Math.PI * i / node_numbers),
                   Math.cos(Math.PI * i / node_numbers),
                   0) for i in range(node_numbers + 1)]
    for i in range(node_numbers):
        arcpath.push(arcpath[node_numbers - 1 - i])

    circ = shapes.circle(radius=0.005)
    extrusion(pos=arcpath, shape=circ, color=color.yellow)
    init_value_box = label(pos=vec(-0.7, -0.5, 0),
                           text='Initial values:\nNumber:',
                           height=25,
                           border=15,
                           font='monospace',
                           color=color.black,
                           linecolor=color.black)


def action(number):
    global init_value_box
    if number > 15:
        number = 15

    def reflection(normal_vector, in_vector):
        fix = dot(in_vector, normal_vector) / norm2(normal_vector)
        return vec(in_vector.x - fix * normal_vector.x * 2,
                   in_vector.y - fix * normal_vector.y * 2,
                   in_vector.z - fix * normal_vector.z * 2)

    def norm2(vector):
        return Math.sqrt(Math.pow(vector.x, 2) +
                         Math.pow(vector.y, 2) +
                         Math.pow(vector.z, 2))

    def dot(vector1, vector2):
        return (vector1.x * vector2.x +
                vector1.y * vector2.y +
                vector1.z * vector2.z)

    init_value_box.text = 'Initial values:\nNumber: ' + str(number)
    for obj in ray_list:
        obj.clear_trail()

    def draw(i):
        ray = sphere(pos=vec(-1, i * 0.05, 0),
                     color=color.blue,
                     radius=1e-06,
                     make_trail=True)
        ray_list.append(ray)
        ray.trail_radius = 0.003
        ray.v = vec(3.0, 0, 0)
        dt = 0.0005

        def step():
            global is_running
            ray.pos = ray.pos + ray.v * dt
            if norm2(ray.pos) >= 1 and ray.pos.x > 0:
                ray.v = reflection(ray.pos, ray.v)

            if ray.pos.y < 0:
                if i < number:
                    draw(i + 1)
                else:
                    is_running = False
            else:
                rate(1000, step)
        step()
    draw(1)


def Number_O(data):
    global is_running
    if data is not None and not is_running:
        is_running = True
        action(data[0])


def setup():
    init()
    profile = {
        'deviceModel': 'Ball-Reflect',
        'idfList': [],
        'odfList': [[Number_O, ['num']]]
    }
    dai(profile)

setup()
