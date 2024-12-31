Power_I = 0
# 以上變數讀取感測器後會自動更新

Luminance_O1 = 0

Luminance_O2 = 0


# 以上變數與actuators連接
# 請勿修改上方程式碼

# use listener for event driven pattern
def on_Power_I(data):
    global Luminance_O1, Luminance_O2
    if data < 3:
        Luminance_O1 = Luminance_O2 = 0
    elif data < 6:
        Luminance_O1 = 1
        Luminance_O2 = 0
    else:
        Luminance_O1 = Luminance_O2 = 1
    update_info()


freq = 120  # 更新頻率(Hz)


# 初始化場景
def scene_init():
    global label_info
    scene = display(width=800, height=700, center=vector(10, 15, 0), background=vector(0, 0, 0))
    scene.forward = vector(-0.5, 0, -0.3)
    label_info = label(pos=vec(10, 20, 0), text='')


# 每秒鐘更新顯示數據
def update_info():
    global label_info
    label_info.text = 'Power_I: {:.2f} \n'.format(Power_I)


scene_init()

# build room
right_wall = box(size=vector(20, 10, 0.3), color=vector(0.5, 0.5, 0.5), texture=textures.rough)
right_wall.pos = vector(15, 10, -1)
left_wall = box(size=vector(0.3, 10, 15), color=vector(0.5, 0.5, 0.5), texture=textures.rough)
left_wall.pos = vector(5, 10, 6.5)
floor = box(size=vector(20, 0.3, 15), color=vector(0.5, 0.5, 0.5), texture=textures.rough)
floor.pos = vector(15, 5, 6.5)
table = extrusion(path=paths.rectangle(width=10, height=8), shape=shapes.rectangle(width=1, height=2),
                  texture=textures.wood_old)
table.pos = vector(15, 6, 6.5)

# create lights
light1 = local_light(pos=vector(5, 15, 20), color=color.yellow)
light2 = local_light(pos=vector(30, 15, 5), color=color.yellow)

# create bulbs
bulb1 = sphere(pos=light1.pos, radius=1, color=vector(0.5, 0.5, 0.5), emissive=True)
rod1 = cylinder(pos=bulb1.pos - vector(0, 3, 0), axis=vector(0, 1, 0), radius=0.5, length=3,
                color=vector(0.5, 0.5, 0.5))
bulb2 = sphere(pos=light2.pos, radius=1, color=vector(0.5, 0.5, 0.5), emissive=True)
rod2 = cylinder(pos=bulb2.pos - vector(0, 3, 0), axis=vector(0, 1, 0), radius=0.5, length=3,
                color=vector(0.5, 0.5, 0.5))
light1_label = label(pos=rod1.pos, text='light1: off\nrequire Power_I: 3')
light2_label = label(pos=rod2.pos, text='light2: off\nrequire Power_I: 6')

cnt = 0
while True:
    rate(freq)
    cnt = cnt + 1
    if cnt % (freq // 5) == 0:
        update_info()
    # update status of lights
    light1.visible = 0 if Luminance_O1 == 0 else 1
    bulb1.color = light1.color if light1.visible else vector(0.5, 0.5, 0.5)
    light1_label.text = 'light1: on\nrequire Power_I: 3' if light1.visible else 'light1: off\nrequire Power_I: 3'
    light2.visible = 0 if Luminance_O2 == 0 else 1
    bulb2.color = light2.color if light2.visible else vector(0.5, 0.5, 0.5)
    light2_label.text = 'light2: on\nrequire Power_I: 6' if light2.visible else 'light2: off\nrequire Power_I: 6'