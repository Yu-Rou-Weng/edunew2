{%- for iv in iv_list -%}
    {%- set _var = iv.giv_name ~ iv.index -%}
    {%- if iv.params | length == 1 -%}
{{ _var }} = {{ iv.params[0].default | safe }}
    {%- elif iv.type == 'array' -%}
        {%- set value_list = [] -%}
        {%- for param in iv.params -%}
        {%- set v0 = param.default -%}
        {%- if value_list.append(v0) -%}{%- endif -%}
        {%- endfor -%}
{{ _var }} = {{ value_list | safe }}
    {%- elif iv.type == 'vector' -%}
        {%- set v0 = iv.params[0].default -%}
        {%- set v1 = iv.params[1].default -%}
        {%- set v2 = iv.params[2].default -%}
{{ _var }} = vec({{ v0 | safe }}, {{ v1 | safe }}, {{ v2 | safe }})
    {%- endif  %}
{% endfor -%}
# 以上變數讀取感測器後會自動更新

{% for _var in output_variables -%}
    {% if _var['type']=='vector' -%}
{{ _var['name'] }} = vec({{ _var['default'][0] }}, {{ _var['default'][1] }}, {{ _var['default'][2] }})
    {% elif _var['type']=='value' -%}
{{ _var['name'] }} = {{ _var['default'][0] }}
    {% else -%}
{{ _var['name'] }} = {{ _var['default'] }}
    {% endif %}
{% endfor -%}
{%- if output_variables| length > 0 -%}
# 以上變數與actuators連接
{%- endif %}
# 請勿修改上方程式碼

class plot3D:
    def __init__(self, f, L, xmin, xmax, ymin, ymax, zmin, zmax):
        # The x axis is labeled y, the z axis is labeled x, and the y axis is labeled z.
        # This is done to mimic fairly standard practive for plotting
        #     the z value of a function of x and y.
        self.f = f
        self.L = L
        
        if not xmin: self.xmin = 0
        else: self.xmin = xmin
        if not xmax: self.xmax = 1
        else: self.xmax = xmax
        if not ymin: self.ymin = 0
        else: self.ymin = ymin
        if not ymax: self.ymax = 1
        else: self.ymax = ymax
        if not zmin: self.zmin = 0
        else: self.zmin = zmin
        if not zmax: self.zmax = 1
        else: self.zmax = zmax
        
        R = self.L/100
        d = self.L-2
        xaxis = cylinder(pos=vec(0,0,0), axis=vec(0,0,d), radius=R, color=color.yellow)
        yaxis = cylinder(pos=vec(0,0,0), axis=vec(d,0,0), radius=R, color=color.yellow)
        zaxis = cylinder(pos=vec(0,0,0), axis=vec(0,d,0), radius=R, color=color.yellow)
        k = 1.02
        h = 0.05*self.L
        text(pos=xaxis.pos+k*xaxis.axis, text='x', height=h, align='center', billboard=True, emissive=True)
        text(pos=yaxis.pos+k*yaxis.axis, text='y', height=h, align='center', billboard=True, emissive=True)
        text(pos=zaxis.pos+k*zaxis.axis, text='z', height=h, align='center', billboard=True, emissive=True)
    
        self.vertices = []
        for x in range(self.L):
            for y in range(self.L):
                val = self.evaluate(x,y)
                self.vertices.append(self.make_vertex( x, y, val ))
        
        self.make_quads()
        self.make_normals()
        
    def evaluate(self, x, y):
        d = self.L-2
        return (d/(self.zmax-self.zmin)) * (self.f(self.xmin+x*(self.xmax-self.xmin)/d, self.ymin+y*(self.ymax-self.ymin)/d)-self.zmin)
    
    def make_quads(self):
        # Create the quad objects, based on the vertex objects already created.
        for x in range(self.L-2):
            for y in range(self.L-2):
                v0 = self.get_vertex(x,y)
                v1 = self.get_vertex(x+1,y)
                v2 = self.get_vertex(x+1, y+1)
                v3 = self.get_vertex(x, y+1)
                quad(vs=[v0, v1, v2, v3])
        
    def make_normals(self):
        # Set the normal for each vertex to be perpendicular to the lower left corner of the quad.
        # The vectors a and b point to the right and up around a vertex in the xy plance.
        for i in range(self.L*self.L):
            x = int(i/self.L)
            y = i % self.L
            if x == self.L-1 or y == self.L-1: continue
            v = self.vertices[i]
            a = self.vertices[i+self.L].pos - v.pos
            b = self.vertices[i+1].pos - v.pos
            v.normal = cross(a,b)
    
    def replot(self):
        for i in range(self.L*self.L):
            x = int(i/self.L)
            y = i % self.L
            v = self.vertices[i]
            v.pos.y = self.evaluate(x,y)
        self.make_normals()

    def make_vertex(self,x,y,value):
        return vertex(pos=vec(y,value,x), color=color.cyan, normal=vec(0,1,0))
        
    def get_vertex(self,x,y):
        return self.vertices[x*self.L+y]
        
    def get_pos(self,x,y):
        return self.get_vertex(x,y).pos

    
def initial():
    global scene, L, t, dt, p
    L = int(Number_I)
    scene.width = scene.height = 600
    scene.center = vec(0.05*L,0.2*L,0)
    scene.range = 1.3*L
    scene.forward = vec(-0.7,-0.5,-1)

    t = 0
    dt = 0.02
    def f(x, y):
        # Return the value of the function of x and y:
        return 0.7+0.2*sin(10*x)*cos(10*y)*sin(5*t)
    
    p = plot3D(f, L, -1, 1, 0, 1, 0, 1) # function, xmin, xmax, ymin, ymax (defaults 0, 1, 0, 1, 0, 1)
initial()

while True:
    rate(30)
    p.replot()
    t += dt
    if L != int(Number_I):
        scene.delete()
        scene = canvas()
        initial()
