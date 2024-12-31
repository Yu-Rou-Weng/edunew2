Humidity_I = 0
Luminance_I = 0
# 以上變數讀取感測器後會自動更新

# 請勿修改上方程式碼

# 初始化場景
def scene_init():
    global label_info, scene
    scene = display(width=800, height=700, center=vector(0, 0, 0),
                    background=vector(0, 0, 0), autoscale=False, range=230)
    scene.lights = [distant_light(direction=vec(0, 3.7, 4), color=color.gray(0.8)),
                    distant_light(direction=vec(0, -1, -2), color=color.gray(0.3))]
    sun_light = local_light(pos=vec(-1600, 1600, 0), color=color.white)
    label_info = label(pos=vec(150, 150, 0), text='')

scene_init()

# draw backgroud
ground = box(length=1600,
             height=20,
             width=1600,
             pos=vector(0, -150, 0),
             texture="/edutalk/static/img/Grass.jpg")
sky = [
       box(length=1600,
          height=1600,
          width=20,
          pos=vector(0, 650, -800),
          texture="/edutalk/static/img/深夜.jpg"),
       box(length=1600,
          height=1600,
          width=20,
          pos=vector(0, 650, -800),
          texture="/edutalk/static/img/剛入夜.jpg"),
       box(length=1600,
          height=1600,
          width=20,
          pos=vector(0, 650, -800),
          texture="/edutalk/static/img/黃昏.jpg"),
      box(length=1600,
          height=1600,
          width=20,
          pos=vector(0, 650, -800),
          texture="/edutalk/static/img/下午.jpg"),
       box(length=1600,
          height=1600,
          width=20,
          pos=vector(0, 650, -800),
          texture="/edutalk/static/img/中午.jpg")
]

# wait for loading textures
scene.visible=False
scene.title="Loading textures ..."
scene.waitfor('textures');
scene.visible=True
scene.title=""

# how luminance affect sky
def Change_background(luminance):
    global sky
    for s in sky:
        s.visible=False
    if luminance <= 20:
        sky[0].visible=True
    elif luminance <= 40:
        sky[1].visible=True
    elif luminance <= 60:
        sky[2].visible=True
    elif luminance <= 80:
        sky[3].visible=True
    else:
        sky[4].visible=True

# set initial sky
Change_background(Luminance_I)

# update sky when receiveing Luminance data
def on_Luminance_I(data):
    if data != None:
        Change_background(data)

# tree data = [[len, pos, dirction], ...]
tree_sample = []

# how to compute tree data
def ortho(a):
    return vector(-a.y, a.x, 0)

def tree(limblen, r, a):
    global tree_sample
    # theta is the "bend angle" for each branching
    theta = 30*pi/180
    fract = .75
    # repeat the branching until the length is shorter than 5
    if limblen > 5:
        tree_sample.append([limblen, r, a])
        # each branch is a cylinder
        # a is a vector that points in the direction of the branch
        # r is the position of the next branch
        r = r+a*limblen
        # rotate turns the pointing direction
        a_temp = rotate(a, angle=theta, axis=ortho(a))
        # here is the recursive magic
        tree(limblen*fract, r, a_temp)
        # now you have to go back to where you were
        a_temp = rotate(a_temp, angle=120*pi/180, axis=a)
        # this does the otherside (also recursive)
        tree(limblen*fract, r, a_temp)

        a_temp = rotate(a_temp, angle=120*pi/180, axis=a)
        tree(limblen*fract, r, a_temp)


# this starts the tree with the starting branchlength = 75
startingbranch = 75
# this is the location of the base
startingposition = vector(0, -150, 0)
# this is the direction of the first branch (up)
startingdirection = vector(0, 1, 0)

# compute tree data in [[len, pos, dirction], ...]
tree(startingbranch, startingposition, startingdirection)

# draw the tree
tree_object = []
# sort by len
def compareByLen(e):
    return -e[0]
tree_sample.pysort(key=compareByLen)

# draw the tree
tree_object = []
for i in range(len(tree_sample)):
    tree_object.append(cylinder(
    	pos=tree_sample[i][1],
        axis=tree_sample[i][2]*tree_sample[i][0],
        radius=0.15*tree_sample[i][0],
        color=vector(100, 42, 42).hat if tree_sample[i][0]>=12 else color.green,
        texture=textures.rough,
        visible=False
    ))


# how humidity affect tree
def create_tree(humidity_rate):
    for i in range(len(tree_sample)):
        if tree_sample[i][0] >= startingbranch*(0.75**humidity_rate):
            tree_object[i].visible=True
        else:
            tree_object[i].visible=False

# set initail tree
create_tree(0)

# grow tree based on humiduty and luminance data
progress = 0
def grow(current_progress):
    return Humidity_I/100*Luminance_I/1000

# update tree when receiving humiduty data
def on_Humidity_I(data):
    global progress
    progress = progress + grow(progress)
    if progress>1:
        progress=1
    create_tree(progress*10)

# animation loop
freq = 50        # 更新頻率(Hz)
cnt = 0

# 更新顯示數據
def update_info():
    global label_info
    label_info.text = 'Humidity_I: {:.2f}\nLuminance_I: {:.2f}\nProgress: {:.2f}'.format(Humidity_I, Luminance_I, progress)

while True:
    rate(freq)
    cnt = cnt + 1
    if cnt % (freq // 5) == 0:
        update_info()