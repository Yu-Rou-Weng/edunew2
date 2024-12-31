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

N = 3 # N by N by N array of atoms
# Surrounding the N**3 atoms is another layer of invisible fixed-position atoms
# that provide stability to the lattice.
k = 1
m = 1
spacing = 1
atom_radius = 0.3*spacing
L0 = spacing-1.8*atom_radius
V0 = pi*(0.5*atom_radius)**2*L0 # initial volume of spring
scene.center = 0.5*(N-1)*vector(1,1,1)
dt = 0.04*(2*pi*sqrt(m/k))

class crystal:
        
    def __init__(self,  N, atom_radius, spacing, momentumRange ):
        self.atoms = []
        self.springs = []
        
        # Create (N+2)^3 atoms in a grid; the outermost atoms are fixed and invisible
        for z in range(-1,N+1,1):
            for y in range(-1,N+1,1):
                for x in range(-1,N+1,1):
                    atom = sphere()
                    atom.pos = vector(x,y,z)*spacing
                    atom.radius = atom_radius
                    atom.color = vector(0,0.58,0.69)
                    if 0 <= x < N and 0 <= y < N and 0 <= z < N:
                        p = vec.random()
                        atom.momentum = momentumRange*p
                    else:
                        atom.visible = False
                        atom.momentum = vec(0,0,0)
                    atom.index = len(self.atoms)
                    self.atoms.append( atom )
        for atom in self.atoms:
            if atom.visible:
                if atom.pos.x == 0:
                    self.make_spring(self.atoms[atom.index-1], atom, False)
                    self.make_spring(atom, self.atoms[atom.index+1], True)
                elif atom.pos.x == N-1:
                    self.make_spring(atom, self.atoms[atom.index+1], False)
                else:
                    self.make_spring(atom, self.atoms[atom.index+1], True)

                if atom.pos.y == 0:
                    self.make_spring(self.atoms[atom.index-(N+2)], atom, False)
                    self.make_spring(atom, self.atoms[atom.index+(N+2)], True)
                elif atom.pos.y == N-1:
                    self.make_spring(atom, self.atoms[atom.index+(N+2)], False)
                else:
                    self.make_spring(atom, self.atoms[atom.index+(N+2)], True)
                    
                if atom.pos.z == 0:
                    self.make_spring(self.atoms[atom.index-(N+2)**2], atom, False)
                    self.make_spring(atom, self.atoms[atom.index+(N+2)**2], True)
                elif atom.pos.z == N-1:
                    self.make_spring(atom, self.atoms[atom.index+(N+2)**2], False)
                else:
                    self.make_spring(atom, self.atoms[atom.index+(N+2)**2], True)
    
    # Create a grid of springs linking each atom to the adjacent atoms
    # in each dimension, or to invisible motionless atoms
    def make_spring(self, start, end, visible):
        spring = helix()
        spring.pos = start.pos
        spring.axis = end.pos-start.pos
        spring.visible = visible
        spring.thickness = 0.05
        spring.radius = 0.5*atom_radius
        spring.length = spacing
        spring.start = start
        spring.end = end
        spring.color = color.orange
        self.springs.append(spring)

c = crystal(N, atom_radius, spacing, 0.1*spacing*sqrt(k/m))

while True:
    rate(60)
    for atom in c.atoms:
        if atom.visible:
            atom.pos = atom.pos + atom.momentum/m*dt
    for spring in c.springs:
        spring.axis = spring.end.pos - spring.start.pos
        L = mag(spring.axis)
        spring.axis = spring.axis.norm()
        spring.pos = spring.start.pos+0.5*atom_radius*spring.axis
        Ls = L-atom_radius
        spring.length = Ls
        Fdt = spring.axis * (k*dt * (1-spacing/L))
        if spring.start.visible:
            spring.start.momentum = spring.start.momentum + Fdt
        if spring.end.visible:
            spring.end.momentum = spring.end.momentum - Fdt
    if N != int(Number_I):
        N = int(Number_I)
        scene.delete()
        scene = canvas(center = 0.5*(N-1)*vector(1,1,1))
        c = crystal(N, atom_radius, spacing, 0.1*spacing*sqrt(k/m))
