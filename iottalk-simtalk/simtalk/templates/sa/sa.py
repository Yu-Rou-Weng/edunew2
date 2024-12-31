import math
import string
from functools import partial
from numpy.random import randint, gamma, normal, uniform

from iottalkpy.dan import NoData

api_url = '{{ api_url }}'
device_name = str(randint(0, 100)) + '.{{ dm_name }}'
device_model = '{{ dm_name }}'
device_addr = '{{ mac_addr }}'
profile ={
    'is_sim': True,
    'do_id': {{ do_id }}
}
idf_list = []

interval = {}
v_dis = {}

def on_register(obj=None):
    print('register successfully')

{% for dfo in dfo_list %}
idf_list.append( '{{ dfo.df_name|safe }}' )
v_dis.setdefault('{{ dfo.df_name|safe }}', [])

# Time Distribution
{{ dfo.df_func_name|safe }}_t_mean = {{ dfo.time_distribution.mean }}
{{ dfo.df_func_name|safe }}_t_var = {{ dfo.time_distribution.var }}
{% if dfo.time_distribution.distribution == 'GA' %}# Gamma Distritbution
{{ dfo.df_func_name|safe }}_t_shape = {{ dfo.df_func_name|safe }}_t_mean * {{ dfo.df_func_name|safe }}_t_mean / {{ dfo.df_func_name|safe }}_t_var
{{ dfo.df_func_name|safe }}_t_scale = {{ dfo.df_func_name|safe }}_t_var / {{ dfo.df_func_name|safe }}_t_mean
{{ dfo.df_func_name|safe }}_t_dist = partial(gamma, {{ dfo.df_func_name|safe }}_t_shape, {{ dfo.df_func_name|safe }}_t_scale)
{% elif dfo.time_distribution.distribution == 'NO' %}# Normal Distribution
{{ dfo.df_func_name|safe }}_t_loc = {{ dfo.df_func_name|safe }}_t_mean
{{ dfo.df_func_name|safe }}_t_scale = math.sqrt({{ dfo.df_func_name|safe }}_t_var)
{{ dfo.df_func_name|safe }}_t_dist = partial(normal, {{ dfo.df_func_name|safe }}_t_loc, {{ dfo.df_func_name|safe }}_t_scale)
{% elif dfo.time_distribution.distribution == 'UN' %}# Uniform Distribution
{{ dfo.df_func_name|safe }}_t_dist = partial(uniform, {{ dfo.time_distribution.min }}, {{ dfo.time_distribution.max }})
{% else %}# Other Distribution: temporay using Gamma
{{ dfo.df_func_name|safe }}_t_shape = {{ dfo.df_func_name|safe }}_t_mean * {{ dfo.df_func_name|safe }}_t_mean / {{ dfo.df_func_name|safe }}_t_var
{{ dfo.df_func_name|safe }}_t_scale = {{ dfo.df_func_name|safe }}_t_var / {{ dfo.df_func_name|safe }}_t_mean
{{ dfo.df_func_name|safe }}_t_dist = partial(gamma, {{ dfo.df_func_name|safe }}_t_shape, {{ dfo.df_func_name|safe }}_t_scale)
{% endif %}
interval.setdefault('{{ dfo.df_func_name|safe }}', {{ dfo.df_func_name|safe }}_t_dist)

{% for vd in dfo.value_distributions %}{# Sensor Data Distribution #}
{{ dfo.df_func_name|safe }}_d_mean = {{ vd.mean }}
{{ dfo.df_func_name|safe }}_d_var = {{ vd.var }}
{% if vd.distribution == 'GA' %}# Gamma Distribution
{{ dfo.df_func_name|safe }}_d_shape = {{ dfo.df_func_name|safe }}_d_mean * {{ dfo.df_func_name|safe }}_d_mean / {{ dfo.df_func_name|safe }}_d_var
{{ dfo.df_func_name|safe }}_d_scale = {{ dfo.df_func_name|safe }}_d_var / {{ dfo.df_func_name|safe }}_d_mean
v_dis['{{ dfo.df_name|safe }}'].append(
    ({{ vd.param_type }},
     partial(gamma, {{ dfo.df_func_name|safe }}_d_shape, {{ dfo.df_func_name|safe }}_d_scale),
     {{ vd.min }},
     {{ vd.max }})
)
{% elif vd.distribution == 'NO' %}# Normal Distribution
{{ dfo.df_func_name|safe }}_d_loc = {{ dfo.df_func_name|safe }}_d_mean
{{ dfo.df_func_name|safe }}_d_scale = math.sqrt({{ dfo.df_func_name|safe }}_d_var)
v_dis['{{ dfo.df_name|safe }}'].append(
    ({{ vd.param_type }},
     partial(normal, {{ dfo.df_func_name|safe }}_d_loc, {{ dfo.df_func_name|safe }}_d_scale),
     {{ vd.min }},
     {{ vd.max }})
)
{% elif vd.distribution == 'UN' %}# Uniform Distribution
v_dis['{{ dfo.df_name|safe }}'].append(
    ({{ vd.param_type }},
     partial(uniform, {{ vd.min }}, {{ vd.max }}),
     {{ vd.min }},
     {{ vd.max }})
)
{% else  %}# Other Distribution: temporay using Gamma
{{ dfo.df_func_name|safe }}_d_shape = {{ dfo.df_func_name|safe }}_d_mean * {{ dfo.df_func_name|safe }}_d_mean / {{ dfo.df_func_name|safe }}_d_var
{{ dfo.df_func_name|safe }}_d_scale = {{ dfo.df_func_name|safe }}_d_var / {{ dfo.df_func_name|safe }}_d_mean
v_dis['{{ dfo.df_name|safe }}'].append(
    ({{ vd.param_type }},
     partial(gamma, {{ dfo.df_func_name|safe }}_d_shape, {{ dfo.df_func_name|safe }}_d_scale),
     {{ vd.min }},
     {{ vd.max }})
)
{% endif %}
{% endfor %}{# endfor Data Distribution #}

def {{ dfo.df_func_name|safe }}():
    data = [max(min(type_(dis_()), max_), min_) for type_, dis_, min_, max_ in v_dis['{{ dfo.df_name|safe }}']]

    return data if len(data) > 1 else data[0]
{% endfor %}{# endfor dfo #}
