
g = 9.8                  #重力加速度9.8m/s^2
theta = 10*pi/180        #初始擺角設定
k = 100000               #彈力常數
m = 1.0                  #擺錘的質量
n = 12                   #單擺個數
d = 0.1                  #每個擺錘之間的間隔為d公尺 
size = d/3.5             #擺錘圓球半徑的大小
L = [0.5, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05]      #每一根擺桿的長度

def SpringForce(r,L):    #擺錘所受的彈力
    return - k*(mag(r)-L) * r / mag(r)

scene = canvas(width = 600, height = 600, center = vector(0, -0.55, d*n/2+0.15), range=0.9, background = vector(0.5, 0.5, 0))     
ceiling = box(pos=vector(0,0,(n-1)*d/2), length=0.03, height=0.001, width=(n-1)*d*1.01, color=vector(0.7,0.7,0.7))    


ball = []      #產生空白的list，稍後從迴圈將擺錘一個一個放進去
string = []    #產生空白的list，稍後從迴圈將擺桿一根一根放進去
for i in range(0,n,1):   #用range指令產生list，內容為0~11，並一一取出每一個元素
    ball.append(sphere(pos=vector(L[i]*sin(theta), -L[i]*cos(theta), d*i), v=vector(0,0,0), radius=size, color=color.blue))
    string.append(cylinder(pos=vector(0,0,d*i), color=vector(0.7,0.7,0.7), radius=0.005))
    #用append指令將物件一個一個擺入list中，i為range這個list的元素

dt = 0.001    #時間間隔
t = 0         #初始時間
while True:
    rate(1/dt)
    t = t+dt            #累計時間
    Ts = t % 60         #計算「秒 sec」
    Tm = int( t/60 )    #計算「分 min」

    a = []    #產生一個空白的list，稍後計算每一個擺錘的加速度，並放入此list中
    for j in range(0,n,1):
        string[j].axis = ball[j].pos - string[j].pos                    #計算每一根擺桿的軸方向
        a.append(vector(0,-g,0)+SpringForce(string[j].axis, L[j])/m)    #計算每一個擺錘的加速度
        ball[j].v = ball[j].v + a[j]*dt            #計算每一個擺錘的速度
        ball[j].pos = ball[j].pos + ball[j].v*dt     #計算每一個擺錘的位置