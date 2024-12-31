
def axisInit():
    global axis, labels
    axis = []
    labels = []
    a = 0
    b = 0
    c = 1
    d = 2
    a = a - 0.5
    b = b - 1.25
    axis.append(arrow(
        pos=vec(a,b,0), 
        axis=vec(c+0.2,0,0), 
        shaftwidth= 0.015, 
        color = color.white
    ))
    axis.append(arrow(
        pos=vec(a,b,0), 
        axis=vec(0,d+0.2,0), 
        shaftwidth= 0.015, 
        color = color.white))
    
    for t in range(0,5):
        axis.append(box(
            pos=vec(a + (t+1)*(4/20), b+d/2, 0), 
            length=0.005, 
            height=d, 
            width=0.01)
    )
    
    for j in range(0,10):
        axis.append(box(
            pos=vec(a + c/2,b + (j+1)*(d/10),0), 
            length=c, 
            height = 0.005,
            width=0.01,
            color=color.gray(0.8)
        ))
        
    for x in range(0,3):
        num = str(round(a+x*(c/5) * 2 * 100 ) / 100)
        labels.append(label(
            pos=vec(a + x*(c/5)*2, b-2*d/20 + 0.1, 0), 
            text = num, 
            height = 20, 
            border = 10, 
            font = 'monospace', 
            color = color.white, 
            box = False)
        )
    
    for y in range(0,6):
        num = str(round(b+y*(d/5)  * 100) /  100 + 0.01)
        labels.append(label(
            pos=vec(a-2*c/40-0.1,b + y*(d/5), 0), 
            text = num, 
            height = 20, 
            border = 10, 
            font = 'monospace', 
            color = color.white, box = False)
        )

def spring_init():
    global scene, ceiling, ball, spring, init_value_box, is_running, size, g,r, spring_coef, dt, mass    
    is_running = True
    g = 9.8
    size = 0.05
    r = 0.5
    spring_coef = 10
    mass = 0.1 
    dt = 0.001
    scene = display(
        width = 700, 
        height = 800, 
        background = vec(0.6, 0.3, 0.2), 
        center = vec(0, -r*0.6, 0),
        range = 1.5
    )
    ceiling = box(length=0.8, height=0.005, width=0.8, color=color.green, pos=vec(0,0.75,0))
    ball = sphere(radius = size, color = color.white)
    ball.pos = vec(0,-2*r+0.75,0)
    spring = helix(radius=0.02, thickness = 0.01, centor = vec(0,0, 0),axis = vec(0,-1,0), pos=vec(0, 0.75, 0))
    init_value_box = label(
        pos=vec(-1.45,1.2,0), 
        text= 'Initial values:\n' + 'Spring_Constant:\n' + '\nMass:', 
        height=20, 
        border=10, 
        font='monospace', 
        color = color.white, 
        xoffset = 1
    )



def action(data):
    global spring_coef
    spring_coef = data[0]
    ball_init()
    step()
    def ball_init():
        ball.pos0 = vec(0, -2*r + 0.75, 0)
        ball.pos = vec(0, -2*r + 0.75, 0)    
        ball.v = vec(0, 0, 0)
        ball.a = vec(0, -g-(spring_coef * (ball.pos.y- ball.pos0.y))/mass , 0) 
    def step():
        global dt, spring_coef, mass, is_running, ball
        init_value_box.text = 'Initial values:\n' + 'SpringConstant:' + str(round(spring_coef, 1)) + '\nMass:' + mass.toFixed(1)
        ball.a = vec(0, -g-(spring_coef * (ball.pos.y- ball.pos0.y))/mass , 0)          
        if is_running == True:
            ball_init()
            is_running = False
        spring.axis = ball.pos - spring.pos
        ball.v = ball.v + ball.a*dt
        ball.pos = ball.pos + (ball.v)*dt
        rate(1000, step) 
    
def SpringConstant(data):
    global is_running, spring_coef , mass
    if data != None:
        is_running = True
        spring_coef = data[0]
        
def Mass(data):
    global is_running, mass
    if data != None and data[0] > 0:
        is_running = True
        mass = data[0]

def setup():
    global axis, labels
    spring_init()
    axisInit()
    profile = {
        'dm_name': 'Spring-SHM',
        'df_list': [SpringConstant, Mass]
    }
    dai(profile)

setup()
action([spring_coef])
