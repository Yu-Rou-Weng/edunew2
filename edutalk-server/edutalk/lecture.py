import logging
import re
import requests
from flask import url_for
from flask import jsonify, request
import json
import logging
import os
from sqlalchemy import func
from datetime import datetime
import pytz
import uuid
import traceback
import markdown
import subprocess
from urllib.parse import urlparse
import requests
import openai
from bs4 import BeautifulSoup
from itertools import chain
from elasticsearch import Elasticsearch
from flask import Blueprint, render_template, abort, jsonify, request, url_for
from flask import render_template_string
from flask_login import current_user
from flask import Flask, jsonify, request
from edutalk import device
from edutalk.config import config
from edutalk.models import Lecture, Template, LectureProject, InputVariable, OutputVariable, HistoricalData
from edutalk.models import Unit
from edutalk.utils import login_required, teacher_required, json_err, ag_ccmapi
from edutalk.exceptions import CCMAPIError
from edutalk.const import sensorOptions, actuatorVarTypeOfDim, actuatorDm
from edutalk.actuator import create_actuator_dfs, check_output_variables, prepare_idfs

import copy
import json
from flask import session

app = Blueprint('lecture', __name__)

db = config.db
log = logging.getLogger('edutalk.lecture')

STORAGE_DIR = '/app/gptshow'
SESSION_ID_FILE = os.path.join(STORAGE_DIR, 'last_session_id.json')

last_session_id = 0
session_serial_numbers = {}


def get_next_session_id():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    if os.path.exists(SESSION_ID_FILE):
        with open(SESSION_ID_FILE, 'r') as f:
            data = json.load(f)
            last_session_id = data.get('last_session_id', 0)
    else:
        last_session_id = 0
        for filename in os.listdir(STORAGE_DIR):
            if filename.startswith("gpt_"):
                parts = filename.split('_')
                if len(parts) > 2:
                    session_id = int(parts[2])
                    last_session_id = max(last_session_id, session_id)
    
    next_session_id = last_session_id + 1
    
    with open(SESSION_ID_FILE, 'w') as f:
        json.dump({'last_session_id': next_session_id}, f)
    
    return next_session_id

def get_or_create_session_id():
    if 'gpt_session_id' not in session:
        session['gpt_session_id'] = get_next_session_id()
    return session['gpt_session_id']

def get_next_serial_number(session_id):
    if session_id not in session_serial_numbers:
        session_serial_numbers[session_id] = 0
    session_serial_numbers[session_id] += 1
    return session_serial_numbers[session_id]

@app.route('/<int:lec_id>/get_sessions', methods=['GET'])
@login_required
def get_sessions(lec_id):
    storage_dir = '/app/gptshow'
    session_ids = []
    for filename in os.listdir(storage_dir):
        if filename.startswith(f"gpt_{lec_id}_") and filename.endswith(".json"):
            session_id = filename.split('_')[2].split('.')[0]
            if session_id not in session_ids:
                session_ids.append(int(session_id))
    session_ids.sort()  
    return jsonify({'sessionIds': session_ids})

@app.route('/<int:lec_id>/get_serial_numbers', methods=['GET'])
@login_required
def get_serial_numbers(lec_id):
    session_id = request.args.get('session_id')
    storage_dir = '/app/gptshow'
    filename = f"gpt_{lec_id}_{session_id}.json"
    file_path = os.path.join(storage_dir, filename)
    
    serial_numbers = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            serial_numbers = [{'serial_number': log_entry['serial_number'], 'mode': log_entry['mode']} for log_entry in data['log']]
    
    serial_numbers.sort(key=lambda x: x['serial_number'])
    return jsonify({'serialNumbers': serial_numbers})

@app.route('/<int:lec_id>/save_cyber_variables', methods=['POST'])
@login_required
def save_cyber_variables(lec_id):
    data = request.json
    lecture = Lecture.query.get(lec_id)
    if not lecture:
        return jsonify({'error': 'Lecture not found'}), 404

    lecture.cyber_variables = data
    db.session.commit()

    return jsonify({'message': 'Cyber variables saved successfully'})

@app.route('/<int:lec_id>/get_idfs', methods=['GET'])
@login_required
def get_idfs(lec_id):
  
    lecture = Lecture.query.get(lec_id)
    if lecture is None:
        abort(404)
 
    idfs = list(set([idf[0] for odf in lecture.joins for idf in lecture.joins[odf]]))
    return jsonify({'idfs': idfs})

@app.route('/<int:lec_id>/get_sensors', methods=['GET'])
@login_required
def get_sensors(lec_id):
  
    sensors = ['Sensor1', 'Sensor2', 'Sensor3']  
    return jsonify({'sensors': sensors})
    
@app.route('/<int:lec_id>/get_log', methods=['GET'])
@login_required
def get_log(lec_id):
    session_id = request.args.get('session_id')
    serial_number = request.args.get('serial_number')
    storage_dir = '/app/gptshow'
    filename = f"gpt_{lec_id}_{session_id}.json"
    file_path = os.path.join(storage_dir, filename)
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            for log_entry in data['log']:
                if str(log_entry['serial_number']) == serial_number:
                    return jsonify({
                        'input': log_entry['input'],
                        'output': log_entry['output'],
                        'mode': log_entry['mode'],
                        'serial_number': log_entry['serial_number']
                    })
    
    return jsonify({'error': 'Log not found'}), 404



@app.route('/genai')
@login_required
def genai():
    return render_template('homepage.html',
                           new_admin=config.new_admin,
                           lesson_data=Lecture.list_())

@app.route('/genai', methods=['GET'], strict_slashes=False)
@login_required
def index():
    return render_template('homepage.html',
                           lesson_data=Lecture.list_())


@app.route('/get_hackmd_content', methods=['GET'])
def get_hackmd_content():
    hackmd_url = request.args.get('url')
    print(f"Attempting to fetch HackMD content from: {hackmd_url}")  # Debugging log
    try:
        response = requests.get(hackmd_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching HackMD content: {e}")
        return jsonify({'error': str(e)}), 400
    return response.text


@app.route('/<int:lec_id>/save_gpt_interaction', methods=['POST'])
@login_required
def save_gpt_interaction(lec_id):
    print(f"Received save_gpt_interaction request for lecture {lec_id}")
    print(f"Request data: {request.data}")
    try:
        data = request.json
        
        storage_dir = '/app/gptshow'
        os.makedirs(storage_dir, exist_ok=True)
        
        taipei_tz = pytz.timezone('Asia/Taipei')
        current_time = datetime.now(taipei_tz)
        
        mode = data.get('mode', '')
        
        if mode == 'initial' or 'gpt_session_id' not in session:
            session['gpt_session_id'] = get_next_session_id()
            session['serial_number'] = 0

        session['serial_number'] += 1
        
        filename = f"gpt_{lec_id}_{session['gpt_session_id']}.json"
        file_path = os.path.join(storage_dir, filename)
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                file_data = json.load(f)
        else:
            file_data = {'session_id': session['gpt_session_id'], 'log': []}
        
        interaction = {
            'input': data.get('input', ''),
            'output': data.get('output', ''),
            'mode': mode,
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),  
            'serial_number': session['serial_number']
        }
        
        file_data['log'].append(interaction)
        
        with open(file_path, 'w') as f:
            json.dump(file_data, f, indent=2)
        
        print(f"GPT Interaction saved: {json.dumps(file_data, indent=2)}")
        
        return jsonify({
            "status": "success", 
            "message": "Interaction saved successfully",
            "new_session_id": session['gpt_session_id'],
            "new_serial_number": session['serial_number']
        })
    except Exception as e:
        print(f"Error saving GPT interaction: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

        
'''@app.route('/<int:lec_id>/save_gpt_interaction', methods=['POST'])
@login_required
def save_gpt_interaction(lec_id):
    print(f"Received save_gpt_interaction request for lecture {lec_id}")
    print(f"Request data: {request.data}")
    try:
        data = request.json
        
        storage_dir = '/app/gptshow'
        os.makedirs(storage_dir, exist_ok=True)
        
        taipei_tz = pytz.timezone('Asia/Taipei')
        current_time = datetime.now(taipei_tz).strftime('%Y%m%d%H%M%S')
        
        filename = f"gpt_{lec_id}_{current_time}.json"
        file_path = os.path.join(storage_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"GPT Interaction saved: {json.dumps(data, indent=2)}")
        
        return jsonify({"status": "success", "message": "Interaction saved successfully"})
    except Exception as e:
        print(f"Error saving GPT interaction: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500'''

@app.route('/reorder', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def reorder():
    '''
    Request::

        {
            'order': [id1, id2, id3, ...],
        }
    '''
    o = request.json.get('order')
    if not o:
        return json_err('Order is empty'), 400

    for idx, id in enumerate(o):
        id_ = str(id)
        lec = Lecture.query.get(id_)
        if lec is None:
            return json_err('Lecture {} not found'.format(id)), 400
        lec.idx = idx

    db.session.commit()
    return jsonify({'state': 'ok'})


@app.route('/<int:id_>/bind', methods=['POST'], strict_slashes=False)
@login_required
def bind(id_):
    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    do_id = x.logger_do['do']['do_id']
    d_id = ag_ccmapi(current_user.id, 'device.get',
                     {'p_id': x.p_id, 'do_id': do_id})[0]['d_id']

    return device.graceful_bind(x, do_id, d_id)


@app.route('/<int:id_>/unbind', methods=['POST'], strict_slashes=False)
@login_required
def unbind(id_):
    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        abort(404)

    do_id = x.logger_do['do']['do_id']
    return device.unbind(x, do_id)


@app.route('/<int:id_>/upload_historical_data', methods=['POST'])
@login_required
def upload_historical_data(id_):
    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    prj = LectureProject.get_by_lec_user(lec, current_user)
    if prj is None:
        abort(404)

    filename = request.json.get('filename')
    if filename is None:
        return json_err('Filename is required'), 400

    data = request.json.get('data')
    if data is None or not data:
        return json_err('Data is required'), 400
    try:
        record = HistoricalData.get_by_project_user(prj, filename)
        if record is None:
            record = HistoricalData(project=prj, name=filename, data=data)
            db.session.add(record)
        else:
            record.data = data
    except Exception as e:
        db.session.rollback()
        log.error(e)
        return json_err('Upload Error\n{}'.format(e)), 400
    else:
        db.session.commit()

    file_list = HistoricalData.query_all(prj)
    return jsonify({'state': 'ok', 'file_list': file_list})


@app.route('/<int:id_>/query_historical_data', methods=['POST'])
@login_required
def query_historical_data(id_):
    '''
    data = {
        idf_name: [
            // table header
            [ 'TimeStamp',  // ISO8601
              'x',
              'y',          // optional
              'z',          // optional
            ],
            // first data
            [ '2022-04-15T16:33:54.488000+08:00',
              0.1,
              0.2,
              0.3,
            ],
            // second data
            ...
        ],
        ...
    }
    '''
    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    prj = LectureProject.get_by_lec_user(lec, current_user)
    if prj is None:
        abort(404)

    filename = request.json.get('filename')
    if filename is None:
        idf_names = request.json.get('idf_names')
        start_time = request.json.get('start_time')
        end_time = request.json.get('end_time')
        data = query_es(idf_names, start_time, end_time)
        return jsonify({'state': 'ok', 'data': data})

    file = HistoricalData.query_file(filename)
    if file is None:
        return json_err(f'File {filename} does not exist.\nPlease try again later.'), 400

    data = file.data
    return jsonify({'state': 'ok', 'data': data})


def query_es(idfs, start_time, end_time):
    # Ref: https://www.elastic.co/guide/en/elasticsearch/
    #       client/python-api/current/config.html#compression
    es = Elasticsearch(hosts='https://{username}:{password}@es01:9200'
                       .format(username='elastic', password=config.es_password),
                       ca_certs="../certs/ca/ca.crt",
                       http_compress=True,
                       request_timeout=1000)

    data = {}
    if not es.indices.exists(index="fluentd"):
        return data

    for df in idfs:
        data[df] = []

        query_str = {
            "_source": [
                "timestamp",
                "from",
                "sample",
            ],
            "sort": [
                {"timestamp": {"format": "strict_date_optional_time_nanos"}}
            ],
            "query": {
                "bool": {
                    "must": {
                        "match": {
                            "from": f"{df}"
                        }
                    },
                    "filter": {
                        "range": {
                            "timestamp": {
                                "gte": f"{start_time}",
                                "lte": f"{end_time}"
                            }
                        }
                    }
                }
            }
        }
        res = es.search(
            index="fluentd",
            body=query_str,
            from_=0,
            size=10000,  # DON'T SET SIZE=100000
            scroll='2m',
            pretty="true"
        )

        total = res['hits']['total']['value']
        if (total == 0):
            continue

        log.info(f'{df} hits: {total}')

        # Ref: https://gist.github.com/hmldd/44d12d3a61a8d8077a3091c4ff7b9307
        # Get the scroll ID
        sid = res['_scroll_id']
        scroll_size = len(res['hits']['hits'])

        if isinstance(res['hits']['hits'][0]['_source']['sample'], list):
            data[df].append(['TimeStamp', 'x', 'y', 'z'])
        else:
            data[df].append(['TimeStamp', 'x'])

        while scroll_size > 0:
            # Before scroll, process current batch of hits
            for hit in res['hits']['hits']:
                target = [hit['_source']['timestamp']]
                if isinstance(hit['_source']['sample'], list):
                    target.append(hit['_source']['sample'][0])
                    target.append(hit['_source']['sample'][1])
                    target.append(hit['_source']['sample'][2])
                else:
                    target.append(hit['_source']['sample'])
                data[df].append(target)

            res = es.scroll(scroll_id=sid, scroll='2m')

            # Update the scroll ID
            sid = res['_scroll_id']

            # Get the number of results that returned in the last scroll
            scroll_size = len(res['hits']['hits'])
    return data


    
@app.route('/<int:lec_id>/rc/token', methods=['GET'])
@login_required
def get_rc_token(lec_id):
    try:
        lecture = Lecture.query.get(lec_id)
        if not lecture:
            return jsonify({'error': 'Lecture not found'}), 404

        # 生成或獲取 token
        token = current_user._token
        if not token:
            token = str(uuid.uuid4().hex)
            current_user._token = token
            db.session.commit()

        # 將 token 和相關信息存儲到 session
        session['rc_token'] = token
        session['lecture_id'] = lec_id

        return jsonify({
            'token': token,
            'rc_url': f'https://emily.iottalk.tw/edutalk/lecture/{lec_id}/rc/?token={token}'
        })

    except Exception as e:
        log.error(f"Error generating RC token: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/edutalk/lecture/<int:lec_id>/create_project', methods=['POST'])
@login_required
def create_lecture_project(lec_id):
    try:
        lecture = Lecture.query.get(lec_id)
        
        if lecture is None:
            return jsonify({'error': 'Lecture not found'}), 404
        
        lecture_project = LectureProject.query.filter_by(lec_id=lec_id).first()
        if lecture_project is None:
            lecture_project = LectureProject(lec_id=lec_id, code="")
            db.session.add(lecture_project)
            db.session.commit()
            log.info(f"LectureProject created successfully for lecture {lec_id}")
            return jsonify({'message': 'LectureProject created successfully'}), 200
        
        log.info(f"LectureProject already exists for lecture {lec_id}")
        return jsonify({'message': 'LectureProject already exists'}), 200
    
    except Exception as e:
        log.error(f"Error creating LectureProject for lecture {lec_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'An error occurred while creating the LectureProject'}), 500


@app.route('/<int:id_>', methods=['GET'], strict_slashes=False)
@login_required
def detail(id_):
    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        log.info(f"Creating LectureProject for lecture {id_}")
        try:
            LectureProject.create(lec, current_user)
            x = LectureProject.get_by_lec_user(lec, current_user)
        except Exception as e:
            log.error(f"Error creating LectureProject: {str(e)}")
            abort(500)

    if x is None or not hasattr(x, 'ido'):
        log.error(f"Invalid LectureProject for lecture {id_}")
        abort(500)

    df_list = {re.sub(r'_', r'-', x['df_name']): x for x in x.ido['df_list']}
    idf_list = list(set([df for df in df_list]))

    idfs = []
    for odf in lec.joins:
        for idf in lec.joins[odf]:
            idfs.append([re.sub(r'-', r'_', idf[0]), idf[2]])

    unit_list = [name for name in chain(*Unit.query.values(Unit.name))]
    file_list = HistoricalData.query_all(x)

    # 准备传递给模板的上下文
    context = {
        'lecture': lec,
        'lesson_data': Lecture.list_(),
        'idfs': idfs,
        'idf_list': [[df, ['magic']] for df in idf_list],
        'csm_url': config.csm_url(),
        'token': current_user.token,
        'unit_list': unit_list,
        'file_list': file_list,
        'sensorOptions': sensorOptions,
        'actuatorVarTypeOfDim': actuatorVarTypeOfDim,
        'actuatorDm': actuatorDm,
        'available_actuators_device': getattr(x, 'available_actuators_device', {}),
        'available_sensors_device': getattr(x, 'available_sensors_device', {})
    }

    # 日志记录，用于调试
    log.debug(f"Template context for lecture {id_}: {context}")

    try:
        return render_template('tutorial.html', **context)
    except Exception as e:
        log.error(f"Error rendering template for lecture {id_}: {str(e)}")
        raise


'''@app.route('/<int:id_>', methods=['GET'], strict_slashes=False)
@login_required
def detail(id_):
    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    x = LectureProject.get_by_lec_user(lec, current_user)
    if x is None:
        LectureProject.create(lec, current_user)
        x = LectureProject.get_by_lec_user(lec, current_user)

    df_list = {re.sub(r'_', r'-', x['df_name']): x for x in x.ido['df_list']}
    idf_list = list(set([df for df in df_list]))

    idfs = []
    for odf in lec.joins:
        for idf in lec.joins[odf]:
            idfs.append([re.sub(r'-', r'_', idf[0]), idf[2]])

    unit_list = [name for name in chain(*Unit.query.values(Unit.name))]

    file_list = HistoricalData.query_all(x)
    return render_template('tutorial.html',
                           lecture=lec,
                           lesson_data=Lecture.list_(),
                           idfs=idfs,
                           idf_list=[[df, ['magic']] for df in idf_list],
                           csm_url=config.csm_url(),
                           token=current_user.token,
                           unit_list=unit_list,
                           file_list=file_list,
                           sensorOptions=sensorOptions,
                           actuatorVarTypeOfDim=actuatorVarTypeOfDim,
                           actuatorDm=actuatorDm,
                           available_actuators_device=x.available_actuators_device,
                           available_sensors_device=x.available_sensors_device
                           )'''


@app.route('/<int:id_>', methods=['DELETE'], strict_slashes=False)
@login_required
@teacher_required
def delete(id_):
    # lock for update
    if db.session.bind.name == 'sqlite':
        db.session.execute('begin immediate transaction')
    lec = Lecture.query.with_for_update().get(id_)

    if lec is None:
        return json_err('Lecture {} not found'.format(id_)), 404

    for x in lec.lecture_projects:
        input_device = ag_ccmapi(x.u_id, 'device.get',
                                 {'p_id': x.p_id, 'do_id': x.ido['do']['do_id']})
        output_device = ag_ccmapi(x.u_id, 'device.get',
                                  {'p_id': x.p_id, 'do_id': x.odo['do']['do_id']})
        if len(input_device) > 0 or len(output_device) > 0:
            return json_err('Someone is still using this lecture.'), 400

        x.delete()

    # delete input/output device model
    ag_ccmapi(current_user.id, 'devicemodel.delete', {'dm': lec.idm})
    ag_ccmapi(current_user.id, 'devicemodel.delete', {'dm': lec.odm})

    '''
    delete input/output device feature which name starts with 'odm'
    '''
    for odf in lec.joins:
        ag_ccmapi(current_user.id, 'devicefeature.delete', {'df': odf})
        for idf in lec.joins[odf]:
            if idf[0].startswith(lec.odm):
                ag_ccmapi(current_user.id, 'devicefeature.delete', {'df': idf[0]})

    '''
    delete idf of vp model(for actuators)
    '''
    for idf in [v['idf'][0] for v in lec.output_variables]:
        ag_ccmapi(current_user.id, 'devicefeature.delete', {'df': idf})

    db.session.delete(lec)
    db.session.commit()

    return jsonify({'state': 'ok', 'url': url_for('root.index')})


@app.route('/<int:id_>/rename', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def rename(id_):
    '''
    Request::

        {
            'name': 'my new name',
        }
    '''
    name = request.json.get('name')
    if not name:
        return json_err('Lecture name cannot be empty'), 400
    if Lecture.isexist(name):
        return json_err('Lecture name already exists'), 400

    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)
    lec.name = name
    db.session.commit()
    return jsonify({'state': 'ok'})


@app.route('/<int:id_>/url', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def update_url(id_):
    '''
    Request::

        {
            url: 'http://.../new_url',
        }
    '''
    url = request.json.get('url')
    if not url:
        return json_err('url cannot be empty'), 400

    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    url_history = lec.url_history

    if url in url_history:
        del url_history[url_history.index(url)]

    url_history.insert(0, url)

    lec.url_history = url_history
    db.session.commit()
    return jsonify({'state': 'ok', 'url_history': url_history})


@app.route('/<int:id_>/video', methods=['POST'], strict_slashes=False)
@login_required
@teacher_required
def update_video_url(id_):
    '''
    Request::

        {
            url: 'http://.../new_url',
        }
    '''
    video_url = request.json.get('video_url')
    if not video_url:
        return json_err('video_url cannot be empty'), 400

    lec = Lecture.query.get(id_)
    if lec is None:
        abort(404)

    video_history = lec.video_history

    if video_url in video_history:
        del video_history[video_history.index(video_url)]

    video_history.insert(0, video_url)

    lec.video_history = video_history
    db.session.commit()
    return jsonify({'state': 'ok', 'video_history': video_history})


@app.route('/<int:id_>/physical', methods=['PUT'], strict_slashes=False)
@login_required
@teacher_required
def physical_feature_binding(id_):
    '''
    Request::
        {
            'odm': {
                'name': 'FOO',
                'dfs': {
                    'name': odf_name,
                    'unit': [
                        param unit,  // y1,
                        param unit,  // y2, optional
                        param unit   // y3, optional
                    ],
                    'type': [
                        param type,  // y1,
                        param type,  // y2, optional
                        param type   // y3, optional
                    ],
                }, ...]
            },
            'idm': {
                'name':'FOORC',
                'dfs': [{
                    'name': idf_name,
                    'type': type,             // optional
                    'min': min,               // optional
                    'max': max,               // optional
                    'default': default value  // optional
                }, ...]
            },
            'joins': {
                odf_name: [
                    [idf_name, fn_name, default value],  // y1,
                    [idf_name, fn_name, default value],  // y2, optional
                    [idf_name, fn_name, default value]   // y3, optional
                ], ...},
            iv_list: [{
                giv_name: name of a global input variable,
                index:   ''  , if no duplicate giv_name
                      integer, otherwise
                params: [{
                    'model': Smartphone or M2,
                    'mac_addr': '' or 'xxxxxx',
                    'device': Range Slider, Input Box, Smartphone, Morsensor or M2,
                    'sensor_unit': sensor unit, // default is 'None'
                    'min': min,                 // default is 0
                    'max': max,                 // default is 10
                    'default': default value,   // default is 5
                    'unit': df unit,            // default is 'None'
                    'type': type,               // default is 'float'
                    'function': join function   // optional, for multidimensional sensor
                }, ...]
            }, ...]
        }
    '''
    log.info('update iv list payload: %s', request.json)

    for f in ('odm', 'idm', 'joins', 'iv_list'):
        if f not in request.json:
            return json_err('field `{}` is required'.format(f)), 400

    iv_list = request.json.get('iv_list', [])
    for iv in iv_list:
        for param in iv.get('params', []):
            if param.get('device') == 'RangeSlider':
                param['device'] = 'Range Slider'
    request.json['iv_list'] = iv_list
    log.info('After conversion iv_list: %s', request.json['iv_list'])
    # checking all fields first, then invoke ccmapi to ``update`` stuff
    msg, typ, error_code = check_payload(request)
    if error_code == 400:
        return json_err(msg, type=typ), error_code

    # lock for update
    if db.session.bind.name == 'sqlite':
        db.session.execute('begin immediate transaction')
    lec = Lecture.query.with_for_update().get(id_)

    if lec is None:
        return json_err('Lecture {} not found'.format(id_)), 404

    if lec.iv_list == request.json['iv_list']:
        return json_err('The settings have not been changed.', type='df'), 400

    for odf in request.json['joins']:
        if len(lec.joins[odf]) != len(request.json['joins'][odf]):
            return json_err('The number of dimensions cannot change.', type='df'), 400

    lec.joins = request.json['joins']
    lec.iv_list = request.json['iv_list']

    # delete device object except logger
    for x in lec.lecture_projects:
        input_device = ag_ccmapi(x.u_id, 'device.get',
                                 {'p_id': x.p_id, 'do_id': x.ido['do']['do_id']})
        if len(input_device) > 0:
            return json_err('Someone is still using this lecture.', type='df'), 400
        ag_ccmapi(x.u_id, 'deviceobject.delete',
                  {'p_id': x.p_id, 'do_id': x.odo['do']['do_id']})
        x.clear_sensors_do()
        x.clear_actuators_do()

    # delete idm
    ag_ccmapi(current_user.id, 'devicemodel.delete', {'dm': lec.idm})

    # create df of idm
    idm = request.json.get('idm')
    if not idm['dfs']:
        return json_err('Feature list cannot be empty', type='df'), 400
    for df in idm['dfs']:
        param = [{'param_type': 'float', 'min': 0, 'max': 10},
                 {'param_type': 'string'}, {'param_type': 'string'}]
        if type(df) is dict and all(limit in df for limit in ('min', 'max')):
            param = [{'param_type': 'float', 'min': df['min'], 'max': df['max']},
                     {'param_type': 'string'}, {'param_type': 'string'}]
        try:
            existing_df = ag_ccmapi(current_user.id, 'devicefeature.get',
                                    {'key': df['name']})
            if type(df) is dict and all(limit in df for limit in ('min', 'max')):
                ag_ccmapi(current_user.id, 'devicefeature.update',
                          {'df_id': existing_df['df_id'], 'df_name': df['name'],
                           'type': 'input', 'parameter': param})
        except CCMAPIError:
            ag_ccmapi(current_user.id, 'devicefeature.create',
                      {'df_name': df['name'], 'type': 'input', 'parameter': param})

    # create new idm
    ag_ccmapi(current_user.id, 'devicemodel.create', {'dm_name': idm['name'],
                                                      'dfs': [{'key': x['name'] if type(x) is dict else x} for x in
                                                              idm['dfs']]})

    for x in lec.lecture_projects:
        x.create_na(x.u_id)

    db.session.commit()

    return jsonify({'state': 'ok', 'url': url_for('root.lecture.detail', id_=lec.id)})
DEFAULT_CODE_TEMPLATE = '''
Acceleration_I = vec(2, 4, 5)
Gyroscope_I1 = [5, 6, 7]
Gyroscope_I2 = 3
# 以上變數讀取感測器後會自動更新

# 請勿修改上方程式碼

freq = 120  # 更新頻率(Hz)

# 初始化場景
def scene_init():
    global label_info
    scene = display(width=800, height=700, center=vector(10, 15, 0), background=vector(0.5, 0.5, 0))
    label_info = label(pos=vec(10, 20, 0), text='')

# 每秒鐘更新顯示數據
def update_info():
    global label_info
    label_info.text = 'Acceleration_I: {} \\nGyroscope_I1: {} \\nGyroscope_I2: {}'.format(Acceleration_I, Gyroscope_I1, Gyroscope_I2)

scene_init()

cnt = 0
while True:
    rate(freq)
    cnt = cnt + 1
    if cnt % (freq // 5) == 0:
        update_info()
'''

@app.route('/<int:lec_id>/delete_and_create', methods=['POST'])
@login_required
@teacher_required
def delete_and_create(lec_id):
    try:
        data = request.json
        log.info(f"收到 lec_id: {lec_id} 的請求, 數據: {data}")

        # 刪除已有的課程
        existing_lecture = Lecture.query.get(lec_id)
        if existing_lecture:
            log.info(f"正在刪除 id 為 {lec_id} 的現有課程")

            # 先查找與該課程相關的所有設備特徵
            related_dfs = set(chain(existing_lecture.joins, [v['idf'][0] for v in existing_lecture.output_variables]))

            # 查找使用這些設備特徵的地方
            in_use_dfs = []
            for df in related_dfs:
                try:
                    df_info = ag_ccmapi(current_user.id, 'devicefeature.get', {'key': df})
                    if df_info['df_type'] == 'output':
                        # 查找使用該 ODF 的 NA
                        na_list = ag_ccmapi(current_user.id, 'networkapplication.list',
                                            {'p_id': existing_lecture.lecture_projects[0].p_id})
                        for na in na_list:
                            for output in na['output']:
                                if output['df_id'] == df_info['df_id']:
                                    # 解除 NA 與 ODF 的關聯
                                    ag_ccmapi(current_user.id, 'networkapplication.update',
                                              {'p_id': existing_lecture.lecture_projects[0].p_id,
                                               'na_id': na['na_id'],
                                               'dfm_list': [{'dfo_id': output['dfo_id'], 'dfmp_list': []}]})
                                    break
                    elif df_info['df_type'] == 'input':
                        # 查找使用該 IDF 的 NA
                        na_list = ag_ccmapi(current_user.id, 'networkapplication.list',
                                            {'p_id': existing_lecture.lecture_projects[0].p_id})
                        for na in na_list:
                            for input_df in na['input']:
                                if input_df['df_id'] == df_info['df_id']:
                                    # 解除 NA 與 IDF 的關聯
                                    ag_ccmapi(current_user.id, 'networkapplication.update',
                                              {'p_id': existing_lecture.lecture_projects[0].p_id,
                                               'na_id': na['na_id'],
                                               'dfm_list': [{'dfo_id': input_df['dfo_id'], 'dfmp_list': []}]})
                                    break
                except CCMAPIError as e:
                    log.error(f"查找設備特徵 {df} 時出錯: {str(e)}")
                    in_use_dfs.append(df)

            if in_use_dfs:
                log.error(f"以下設備特徵正在被使用,無法刪除: {', '.join(in_use_dfs)}")
                return jsonify({'error': f'以下設備特徵正在被使用,無法刪除: {", ".join(in_use_dfs)}'}), 400

            # 刪除課程相關的所有設備特徵
            for df in related_dfs:
                log.info(f"正在刪除設備特徵 {df}")
                ag_ccmapi(current_user.id, 'devicefeature.delete', {'df': df})

            db.session.delete(existing_lecture)
            db.session.commit()

        # 獲取代碼模板
        code_template = get_code_template(data.get('code', 'New'))

        # 創建新課程
        new_lecture = Lecture(
            name=data['name'],
            odm=data['odm']['name'],
            idm=data['idm']['name'],
            joins=json.dumps(data.get('joins', {})),
            code=code_template,
            iv_list=json.dumps(data.get('iv_list', [])),
            output_variables=json.dumps(data.get('output_variables', [])),
            idx=len(Lecture.query.all()) + 1
        )
        db.session.add(new_lecture)
        db.session.commit()

        # 確保設備模型和特徵存在
        try:
            # 創建或更新設備特徵
            df_ids = []
            for df in data['odm']['dfs'] + data['idm']['dfs']:
                df_data = {
                    'df_name': df['name'],
                    'type': 'output' if df in data['odm']['dfs'] else 'input',
                    'parameter': [{'param_type': t} for t in df['type']],
                    'comment': ''
                }
                log.info(f"正在創建或更新設備特徵 {df['name']}，數據: {json.dumps(df_data)}")

                # 先檢查設備特徵是否已經存在
                try:
                    existing_df = ag_ccmapi(current_user.id, 'devicefeature.get', {'key': df['name']})
                    log.info(f"設備特徵 {df['name']} 已經存在")

                    # 如果存在,則先刪除
                    log.info(f"正在刪除設備特徵 {df['name']}")
                    ag_ccmapi(current_user.id, 'devicefeature.delete', {'df': df['name']})
                except CCMAPIError:
                    log.info(f"設備特徵 {df['name']} 不存在，準備創建新的")

                # 然後創建新的設備特徵
                df_id = ag_ccmapi(current_user.id, 'devicefeature.create', df_data)
                df_ids.append(df_id)

            # 創建 ODM
            odm_data = {
                'dm_name': new_lecture.odm,
                'dfs': [{'df_id': df_id, 'df_parameter': []} for df_id in df_ids[:len(data['odm']['dfs'])]]
            }
            log.info(f"正在創建 ODM，數據: {json.dumps(odm_data)}")
            odm_id = ag_ccmapi(current_user.id, 'devicemodel.create', odm_data)
            
            # 創建 IDM
            idm_data = {
                'dm_name': new_lecture.idm,
                'dfs': [{'df_id': df_id, 'df_parameter': []} for df_id in df_ids[len(data['odm']['dfs']):]]
            }
            log.info(f"正在創建 IDM，數據: {json.dumps(idm_data)}")
            idm_id = ag_ccmapi(current_user.id, 'devicemodel.create', idm_data)

        except CCMAPIError as e:
            log.error(f"創建設備模型或特徵時出錯: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'無法創建設備模型或特徵: {str(e)}'}), 500

        # 創建新的 LectureProject
        try:
            log.info(f"嘗試為課程 {new_lecture.id} 創建 LectureProject")
            project = LectureProject.create(new_lecture, current_user)
            if project:
                project.code = code_template
                db.session.commit()
                log.info(f"LectureProject 創建成功: {project.id}")
            else:
                raise Exception("LectureProject.create 返回 None")
        except Exception as e:
            log.error(f"創建 LectureProject 時出錯: {str(e)}")
            log.error(traceback.format_exc())
            db.session.rollback()
            return jsonify({'error': f'無法創建 LectureProject: {str(e)}'}), 500

        log.info(f"課程和 LectureProject 成功創建，lec_id: {lec_id}")

        return jsonify({'message': '課程創建成功', 'id': new_lecture.id}), 200

    except Exception as e:
        log.error(f"創建課程時發生錯誤: {e}")
        log.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/check-and-create', methods=['POST'])
@login_required
@teacher_required
def check_and_create_lecture():
    name = request.json.get('name')
    if not name:
        return jsonify({'error': 'Lecture name is required'}), 400
    
    existing_lecture = Lecture.query.filter_by(name=name).first()
    if existing_lecture:
        return jsonify({'exists': True}), 200
    
    # 获取最大的 lec_id 并创建新课程
    max_lec_id = db.session.query(func.max(Lecture.id)).scalar() or 0
    new_lec_id = max_lec_id + 1
    
    new_lecture = Lecture(
        id=new_lec_id,
        name=name,
        idx=len(Lecture.query.all()) + 1,
        # 其他必要的字段...
    )
    db.session.add(new_lecture)
    db.session.commit()
    
    return jsonify({
        'exists': False,
        'new_id': new_lec_id
    }), 200

@app.route('/check-name', methods=['POST'])
@login_required
def check_lecture_name():
    name = request.json.get('name')
    exists = Lecture.query.filter(Lecture.name == name).first() is not None
    return jsonify({'exists': exists})
@app.route('/save-name', methods=['POST'])
@login_required
def save_lecture_name():
    try:
        name = request.json.get('name')
        lec_id = request.json.get('lecture_id')  # 添加这行来获取 lecture_id
        if not name or not lec_id:
            return jsonify({'success': False, 'message': 'Name or lecture ID is missing'}), 400
        
        lecture = Lecture.query.get(lec_id)
        if lecture:
            lecture.name = name
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Lecture not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/create-ajax', methods=['POST'])
@login_required
@teacher_required
def create_lecture_ajax():
    name = request.json.get('name')
    if not name:
        return jsonify({'error': 'Lecture name is required'}), 400
    
    new_lecture = Lecture(name=name, idx=len(Lecture.query.all()) + 1)
    db.session.add(new_lecture)
    db.session.commit()
    
    return jsonify({'message': 'Lecture created successfully', 'id': new_lecture.id})

@app.route('/lecture/create', methods=['PUT'])
def create_lecture():
    data = request.json
    
    # 檢查請求的課程 ID 是否已存在
    if Lecture.query.get(data.get('id')):
        return jsonify({
            'error': 'Lecture ID already exists',
            'reason': 'The requested lecture ID is already taken'
        }), 400
        
    # 創建新課程
    new_lecture = Lecture(
        id=data.get('id'),  # 使用請求中指定的 ID
        name=data.get('name'),
        url=data.get('url'),
        odm=data.get('odm'),
        idm=data.get('idm'),
        joins=data.get('joins'),
        code=data.get('code', 'New'),
        iv_list=data.get('iv_list', []),
        output_variables=data.get('output_variables', [])
    )
    
    try:
        db.session.add(new_lecture)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'url': url_for('root.lecture.show', id_=new_lecture.id)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Database error',
            'reason': str(e)
        }), 500
def get_code_template(template_name):
    # 這裡你需要實現一個函數來根據模板名稱返回相應的代碼模板
    # 例如，你可以有一個預定義的字典或從數據庫中獲取模板
    templates = {
        'New': '''
Acceleration_I = vec(2, 4, 5)
Gyroscope_I1 = [5, 6, 7]
Gyroscope_I2 = 3
# 以上變數讀取感測器後會自動更新

# 請勿修改上方程式碼

freq = 120  # 更新頻率(Hz)

# 初始化場景
def scene_init():
    global label_info
    scene = display(width=800, height=700, center=vector(10, 15, 0), background=vector(0.5, 0.5, 0))
    label_info = label(pos=vec(10, 20, 0), text='')

# 每秒鐘更新顯示數據
def update_info():
    global label_info
    label_info.text = 'Acceleration_I: {} \\nGyroscope_I1: {} \\nGyroscope_I2: {}'.format(Acceleration_I, Gyroscope_I1, Gyroscope_I2)

scene_init()

cnt = 0
while True:
    rate(freq)
    cnt = cnt + 1
    if cnt % (freq // 5) == 0:
        update_info()
'''
        # 你可以添加更多模板
    }
    return templates.get(template_name, templates['New'])  # 如果沒找到模板，使用 'New' 模板

@app.route('/<int:id_>/actuator', methods=['PUT'], strict_slashes=False)
@login_required
@teacher_required
def actuator_feature_binding(id_):
    """
    payload:
        {
            'output_variables': {
                'var': name of actuator variable, # search key
                'actuator': '',  # dm of actuator want to change
                'odf': '',  # odf of actuator want to change
                # other fields are ignored
            }
        }
    """
    log.debug('update iv list payload: %s', request.json)

    for f in ('output_variables',):
        if f not in request.json:
            return json_err('field `{}` is required'.format(f)), 400

    output_variables = request.json['output_variables']

    # lock for update
    if db.session.bind.name == 'sqlite':
        db.session.execute('begin immediate transaction')
    lec = Lecture.query.with_for_update().get(id_)

    if lec is None:
        return json_err('Lecture {} not found'.format(id_)), 404

    new_output_variables = []
    for actuator_var in output_variables:
        old_var = next(v for v in lec.output_variables if v['name'] == actuator_var['name'])
        if not old_var:
            return json_err('Actuator variable {} is not exist'
                            .format(actuator_var['name'])), 400
        else:
            new_var = copy.deepcopy(old_var)
            new_var['actuator'] = actuator_var['actuator']
            new_var['odf'] = actuator_var['odf']
            new_var['mac_addr'] = actuator_var['mac_addr']
            # new_var['params'] = actuator_var['params'] if 'params' in actuator_var else []
            new_output_variables.append(new_var)

    # checking new_output_variables
    msg = check_output_variables(new_output_variables)
    if msg:
        return json_err(msg, type='actuator'), 400

    if lec.output_variables == new_output_variables:
        return json_err('The settings have not been changed.', type='actuator'), 400
    else:
        lec.output_variables = new_output_variables
    '''
    # build mapping
    odf_to_idf_mapping = {}
    count, pos = {}, {}
    for var in lec.output_variables:
        for p in var['params']:
            if not p['mac_addr'] or p['model'] not in actuatorDm or \
                    p['odf'] not in actuatorDm[p['model']]['odfs']:
                continue
            dim = actuatorDm[p['model']]['odfs'][p['odf']]['dim']
            # count dim
            if dim not in count:
                count[dim] = 0
                pos[dim] = 1
            if p['model'] not in odf_to_idf_mapping:
                odf_to_idf_mapping[p['model']] = {}
            if p['mac_addr'] not in odf_to_idf_mapping[p['model']]:
                odf_to_idf_mapping[p['model']][p['mac_addr']] = {}
            if p['odf'] not in odf_to_idf_mapping[p['model']][p['mac_addr']]:
                odf_to_idf_mapping[p['model']][p['mac_addr']][p['odf']] = \
                    {'idf': 'Dim{0}-I{1}'.format(dim, pos[dim]), 'dim': dim}
                count[dim] += 1
                pos[dim] += 1
    lec.odf_to_idf_mapping = odf_to_idf_mapping'''

    # delete device object except logger
    for x in lec.lecture_projects:
        input_device = ag_ccmapi(x.u_id, 'device.get',
                                 {'p_id': x.p_id, 'do_id': x.ido['do']['do_id']})
        if len(input_device) > 0:
            return json_err('Someone is still using this lecture.', type='actuator'), 400
        ag_ccmapi(x.u_id, 'deviceobject.delete',
                  {'p_id': x.p_id, 'do_id': x.odo['do']['do_id']})
        x.clear_sensors_do()
        x.clear_actuators_do()
    '''
    # create idfs for animation da
    dfs = []
    for d in count:
        dfs.extend(prepare_idfs(current_user.id, d, count[d]))
    # collect odfs
    dfs.extend([x['df_name'] for x in
                ag_ccmapi(current_user.id, 'devicemodel.get', {'key': lec.odm})['df_list']
                if x['df_type'] == 'output'])
    log.info(dfs)
    # todo: delete odm
    # ag_ccmapi(current_user.id, 'devicemodel.delete', {'dm': lec.odm})
    # todo: create odm
    # ag_ccmapi(current_user.id, 'devicemodel.create', {'dm_name': lec.odm, 'dfs': dfs})
    '''
    for x in lec.lecture_projects:
        x.create_na(x.u_id)

    db.session.commit()

    return jsonify({'state': 'ok', 'url': url_for('root.lecture.detail', id_=lec.id)})


@app.route('/create', methods=['GET'], strict_slashes=False)
@login_required
@teacher_required
def create_page():
    t_list = {}
    for dm in chain(*Template.query.values(Template.dm)):
        iv_list = Template.query.filter_by(dm=dm).first().iv_list
        t_list[dm] = {'iv_list': iv_list}

    frequency = current_user.frequency_of_giv
    global_iv_list = {iv.name: {'selected': 0,
                                'frequency': frequency[iv.name]['frequency']
                                if iv.name in frequency else 0}
                      for iv in InputVariable.query.order_by(InputVariable.id).all()}

    frequency = current_user.frequency_of_output_var
    actuator_var_list = [{'name': ov.name, 'frequency': frequency[ov.name]['frequency']
    if ov.name in frequency else 0}
                         for ov in OutputVariable.query.order_by(OutputVariable.id).all()]
    actuator_var_list.sort(key=lambda ov: ov['frequency'], reverse=True)
    actuator_var_list = [ov['name'] for ov in actuator_var_list]

    unit_list = [name for name in chain(*Unit.query.values(Unit.name))]

    return render_template('tutorial.html',
                           lecture=None,
                           lesson_data=Lecture.list_(),
                           t_list=t_list,
                           global_iv_list=global_iv_list,
                           output_var_list=actuator_var_list,
                           unit_list=unit_list,
                           )
@app.route('/create_and_redirect', methods=['GET'])
@login_required
@teacher_required
def create_and_redirect():
    try:
        log.info("Attempting to get the maximum lecture ID")
        
        # 获取最大的 lec_id
        max_lec_id = db.session.query(func.max(Lecture.id)).scalar() or 0
        
        log.info(f"Maximum lecture ID: {max_lec_id}")
        
        # 构造重定向URL，使用最大的 lec_id
        redirect_url = url_for('root.lecture.detail', id_=max_lec_id)
        
        log.info(f"Redirect URL: {redirect_url}")
        
        # 返回JSON响应，包含重定向URL
        return jsonify({'redirect_url': redirect_url})
    
    except Exception as e:
        log.error(f"Error in create_and_redirect: {str(e)}")
        log.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@app.route('/create', methods=['PUT'], strict_slashes=False)
@login_required
@teacher_required
def create():
    log.info('create lecture payload: %s', request.json)

    # 基本檢查
    for f in ('name', 'odm', 'idm', 'joins', 'code', 'iv_list', 'output_variables'):
        if f not in request.json:
            return json_err('field `{}` is required'.format(f)), 400

    name = request.json['name']
    if not name:
        return json_err('Lecture name is required', type='lecture'), 400
    elif Lecture.isexist(name):
        return json_err('duplicated lecture name', type='lecture'), 400

    url = request.json.get('url', '')

    msg, typ, error_code = check_payload(request)
    if error_code == 400:
        return json_err(msg, type=typ), error_code

    try:
        # 先檢查並清理已存在的設備模型
        odm_name = request.json['odm']['name']
        idm_name = request.json['idm']['name']

        def safely_delete_model(model_name):
            try:
                ag_ccmapi(current_user.id, 'devicemodel.get', {'key': model_name})
                ag_ccmapi(current_user.id, 'devicemodel.delete', {'dm': model_name})
                log.info(f"Deleted existing model: {model_name}")
            except CCMAPIError as e:
                if 'not found' not in str(e).lower():
                    raise

        # 刪除已存在的模型
        safely_delete_model(odm_name)
        safely_delete_model(idm_name)

        # 清理舊的 device features
        def safely_delete_feature(feature_name):
            try:
                ag_ccmapi(current_user.id, 'devicefeature.delete', {'df': feature_name})
                log.info(f"Deleted existing feature: {feature_name}")
            except CCMAPIError as e:
                if 'not found' not in str(e).lower():
                    raise

        # 清理 ODM 相關的 features
        for df in request.json['odm']['dfs']:
            safely_delete_feature(df['name'])

        # 清理 IDM 相關的 features
        for df in request.json['idm']['dfs']:
            safely_delete_feature(df['name'])

        # 建立 actuator features
        actuator_dfs, output_variables = create_actuator_dfs(
            current_user.id,
            request.json['odm']['name'],
            request.json['output_variables']
        )

        # 建立新的 device features
        for dm, typ in (('odm', 'output'), ('idm', 'input')):
            x = request.json.get(dm)
            if not x['dfs']:
                return json_err('Feature list cannot be empty', type='df'), 400

            for df in x['dfs']:
                try:
                    if type(df['type']) is list:
                        param = [{'param_type': pt, 'min': 0, 'max': 10} for pt in df['type']]
                    elif all(limit in df for limit in ('min', 'max')):
                        param = [
                            {'param_type': df['type'], 'min': df['min'], 'max': df['max']},
                            {'param_type': 'string'},
                            {'param_type': 'string'}
                        ]
                    else:
                        param = [
                            {'param_type': df['type'], 'min': 0, 'max': 10},
                            {'param_type': 'string'},
                            {'param_type': 'string'}
                        ]
                    
                    ag_ccmapi(current_user.id, 'devicefeature.create',
                            {'df_name': df['name'], 'type': typ, 'parameter': param})
                    log.info(f"Created new feature: {df['name']}")
                except CCMAPIError as e:
                    log.error(f"Error creating feature {df['name']}: {str(e)}")
                    raise

        # 建立新的 device models
        try:
            # 建立 IDM
            dm = request.json['idm']
            ag_ccmapi(current_user.id, 'devicemodel.create', {
                'dm_name': dm['name'],
                'dfs': [{'key': x['name'] if isinstance(x, dict) else x} for x in dm['dfs']]
            })
            log.info(f"Created IDM: {dm['name']}")

            # 建立 ODM
            dm = request.json['odm']
            ag_ccmapi(current_user.id, 'devicemodel.create', {
                'dm_name': dm['name'],
                'dfs': [{'key': x['name'] if isinstance(x, dict) else x} for x in actuator_dfs + dm['dfs']]
            })
            log.info(f"Created ODM: {dm['name']}")

        except CCMAPIError as e:
            log.error(f"Error creating device model: {str(e)}")
            raise

        # 準備 VPython 代碼
        odm = request.json['odm']
        odfs = list(map(lambda x: [re.sub(r'-', r'_', x['name']), x['unit']], odm['dfs']))
        odm_temp = request.json['code']
        temp = Template.query.filter_by(dm=odm_temp).first()
        
        vp_code = render_template_string(
            temp.code,
            dm_name=odm['name'],
            iv_list=request.json['iv_list'],
            odf_list=odfs,
            output_variables=output_variables,
            trim_blocks=True,
            lstrip_blocks=True
        )

        # 創建 Lecture 記錄
        lec = Lecture(
            name=name,
            idx=len(Lecture.query.all()) + 1,
            url_history=[url] if url != '' else [],
            idm=request.json['idm']['name'],
            odm=request.json['odm']['name'],
            joins=request.json['joins'],
            code=vp_code,
            iv_list=request.json['iv_list'],
            output_variables=output_variables
        )
        
        db.session.add(lec)
        db.session.commit()

        # 更新使用頻率
        frequency = current_user.frequency_of_giv
        for giv in list(set([iv['giv_name'] for iv in request.json['iv_list']])):
            if giv in frequency:
                frequency[giv]['frequency'] += 1
            else:
                frequency[giv] = {'frequency': 1}
        current_user.frequency_of_giv = frequency

        frequency = current_user.frequency_of_output_var
        for gov in [x['key'] for x in request.json['output_variables']]:
            if gov in frequency:
                frequency[gov]['frequency'] += 1
            else:
                frequency[gov] = {'frequency': 1}
        current_user.frequency_of_output_var = frequency
        
        db.session.commit()

        return jsonify({
            'state': 'ok',
            'url': url_for('root.lecture.detail', id_=lec.id)
        })

    except CCMAPIError as e:
        log.error(f"CCM API error: {str(e)}")
        db.session.rollback()
        return json_err(str(e)), 500
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}")
        db.session.rollback()
        return json_err(str(e)), 500

@app.app_template_filter()
def todf_list(x):
    return '[{}]'.format(', '.join('[{}, {}]'.format(a[0], a[1]) for a in x))


@app.route('/iv', methods=['PUT'], strict_slashes=False)
@login_required
@teacher_required
def new_iv():
    '''
    Request::

        {
            'name': 'Radius',
        }
    '''
    from keyword import iskeyword

    name = request.json.get('name')
    if name.isidentifier() and not iskeyword(name) and name[:1].isupper() and name.endswith("_I"):
        new_iv = InputVariable(name=name)
        db.session.add(new_iv)
        db.session.commit()
        return jsonify({'state': 'ok'})
    return json_err('Variable\'s name should follow python rule, start with UpperCase, and end with _I.'), 400


@app.route('/ov', methods=['PUT'], strict_slashes=False)
@login_required
@teacher_required
def new_ov():
    '''
    Request::

        {
            'name': 'Radius',
        }
    '''
    from keyword import iskeyword

    name = request.json.get('name')
    if name.isidentifier() and not iskeyword(name) and name[:1].isupper() and name.endswith("_O"):
        new_ov = OutputVariable(name=name)
        db.session.add(new_ov)
        db.session.commit()
        return jsonify({'state': 'ok'})
    return json_err('Variable\'s name should follow python rule, start with UpperCase, and end with _O.'), 400


@app.route('/unit', methods=['PUT'], strict_slashes=False)
@login_required
@teacher_required
def new_unit():
    '''
    Request::

        {
            'name': 'all',
        }
    '''
    new_unit = Unit(name=request.json.get('name'))
    db.session.add(new_unit)
    db.session.commit()
    return jsonify({'state': 'ok'})

@app.route('/<int:lec_id>/hackmd', methods=['GET'])
@login_required
def get_hackmd_url(lec_id):
    try:
        lecture = Lecture.query.get(lec_id)
        if lecture is None:
            abort(404)

        hackmd_url = lecture.url
        return jsonify({'hackmd_url': hackmd_url})

    except Exception as e:
        log.error(f"Error occurred while getting HackMD URL for lecture {lec_id}: {e}")
        log.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred.'}), 500

'''@app.route('/<int:id_>/hackmd', methods=['GET'])
@login_required
def get_hackmd_url(id_):
    lecture = Lecture.query.get(id_)
    if lecture is None:
        abort(404)

    hackmd_url = lecture.url  

    return jsonify({'hackmd_url': hackmd_url})

@app.route('/<int:id_>/hackmd/html', methods=['GET'])
@login_required
def get_hackmd_html(id_):
    lecture = Lecture.query.get(id_)
    if lecture is None:
        abort(404)

    hackmd_url = lecture.url

    try:
        response = requests.get(hackmd_url)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 400

    soup = BeautifulSoup(html_content, 'html.parser')

    body_content = soup.body.decode_contents()

    return jsonify({'html': body_content})'''

@app.route('/<int:lec_id>/hackmd/markdown', methods=['GET'])
@login_required
def get_hackmd_markdown(lec_id):
    try:
        # 新增：獲取查詢參數
        include_mapping = request.args.get('include_mapping', 'false').lower() == 'true'
        
        lecture = Lecture.query.get(lec_id)
        if lecture is None:
            abort(404)

        hackmd_url = lecture.url
        if not hackmd_url:
            return jsonify({'error': 'No HackMD URL provided'}), 400

        try:
            response = requests.get(hackmd_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content_element = soup.find('div', {'class': 'markdown-body'})
            
            if not content_element:
                raise ValueError('Could not find markdown content in HackMD page')
                
            markdown_content = content_element.get_text()

            # 添加基本格式
            final_content = f"1. Screen Settings:\nSet the canvas width to 700 and height to 400. Do not change the canvas size.\n\n2. Object Motion & Parameter Settings:\nCreate a VPython animation to illustrate the following physics experiment:\n\n{markdown_content}"

            # 只有當 include_mapping 為 true 時才添加 mapping info
            if include_mapping:
                try:
                    storage_dir = '/app/gptshow'
                    filename = f"mapping_{lec_id}.json"
                    file_path = os.path.join(storage_dir, filename)
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            mapping_data = json.load(f)
                            mapping_info = mapping_data.get('cyberInputMappingInfo')
                            if mapping_info:
                                final_content = f"{final_content}{mapping_info}"
                                log.info(f"Added mapping info for lecture {lec_id}")
                except Exception as e:
                    log.error(f"Error reading mapping info: {str(e)}")

            return jsonify({
                'markdown': final_content,
                'has_mapping': include_mapping
            })

        except requests.exceptions.RequestException as e:
            log.error(f"Error fetching HackMD content: {str(e)}")
            return jsonify({
                'error': 'Failed to fetch HackMD content',
                'details': str(e)
            }), 400

    except Exception as e:
        log.error(f"Server error: {str(e)}")
        return jsonify({
            'error': 'Server error',
            'details': str(e)
        }), 500
        
@app.route('/<int:lec_id>/save_mapping', methods=['POST'])
@login_required
def save_mapping(lec_id):
    try:
        data = request.json
        mapping_info = data.get('cyberInputMappingInfo')
        next_lecture_id = data.get('nextLectureId')
        
        if not mapping_info:
            return jsonify({'error': 'Mapping info is required'}), 400
            
        if not next_lecture_id:
            return jsonify({'error': 'Next lecture ID is required'}), 400
            
        storage_dir = '/app/gptshow'
        os.makedirs(storage_dir, exist_ok=True)
        
        # 保存當前課程的映射 
        current_filename = f"mapping_{lec_id}.json"
        current_file_path = os.path.join(storage_dir, current_filename)
        
        # 保存新課程的映射
        next_filename = f"mapping_{next_lecture_id}.json"
        next_file_path = os.path.join(storage_dir, next_filename)
        
        mapping_data = {
            'cyberInputMappingInfo': mapping_info,
            'created_at': datetime.now(pytz.UTC).isoformat()
        }
        
        # 保存到兩個位置
        with open(current_file_path, 'w') as f:
            json.dump(mapping_data, f, indent=2)
            
        with open(next_file_path, 'w') as f:
            json.dump(mapping_data, f, indent=2)
            
        return jsonify({
            'status': 'success',
            'message': 'Mapping info saved for both current and next lecture'
        })
        
    except Exception as e:
        log.error(f"Error saving mapping info: {str(e)}")
        log.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500
        
def translate_with_gpt(markdown_content):
    try:
        openai.api_key = "sk-proj-NrKa2xS0TaOc0bLdlLaoT3BlbkFJl6Gn4w9f9kweuoccRksI"
        question = "Translate the following content to english\n\n" + markdown_content
        
        answerresponse = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",    
            messages=[
                {"role": "system", "content": "You are now a professional English translator"},
                {"role": "user", "content": question}
            ],
            temperature=0.7,                # diversity related
            top_p=1,                   # diversity related
            n=1,                          # num of response
        )
        
        translated_text = answerresponse.choices[0].message['content'].strip()
        return translated_text
    except Exception as e:
        log.exception(f"Error occurred while translating with GPT: {str(e)}")
        return markdown_content  

@app.route('/<int:lec_id>/code', methods=['POST'], strict_slashes=False)
@login_required
def code_update(lec_id):
    lecture = Lecture.query.get(lec_id)
    x = LectureProject.get_by_lec_user(lecture, current_user)
    if x is None:
        abort(404)

    code = request.json.get('code')
    if not code:
        abort(400)

    x.code = code
    db.session.commit()

    return jsonify({'state': 'ok'})

@app.route('/<int:lec_id>/submit_to_gpt', methods=['POST'])
@login_required
def submit_to_gpt(lec_id):
    try:
        data = request.get_json()
        if not data or not data.get('prompt'):
            return jsonify({'error': 'Invalid request data'}), 400

        prompt = data['prompt']
        mode = data.get('mode', 'initial')

        log.info(f"Processing GPT request for lecture {lec_id}")
        log.info(f"Prompt: {prompt[:100]}...") # Log first 100 chars of prompt

        try:
            openai.api_key = "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"

            
            messages = [
                {"role": "system", "content": "You are a VPython expert. Generate only the Python code without any explanations or markdown formatting."},
                {"role": "user", "content": prompt}
            ]

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                top_p=1,
                n=1
            )

            program = response.choices[0].message['content'].strip()
            program = program.replace('```python', '').replace('```', '').strip()

            log.info("Successfully generated program")
            log.debug(f"Generated program: {program[:100]}...") # Log first 100 chars

            return jsonify({
                'program': program,
                'mode': mode
            })

        except Exception as e:
            log.error(f"OpenAI API error: {str(e)}")
            return jsonify({'error': f'GPT API error: {str(e)}'}), 500

    except Exception as e:
        log.error(f"Server error in submit_to_gpt: {str(e)}")
        log.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/<int:lec_id>/get_controllable_variables', methods=['POST'])
@login_required
def get_controllable_variables(lec_id):
    # Code to extract controllable variables based on the prompt
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        # Here, construct the GPT prompt for fetching controllable variables
        question = f"In this experiment, what variables can be controlled? Just give the variable names. No need to explain them. Please provide the returned content in JSON format.\n\n{prompt}"

        openai.api_key = "sk-proj-NrKa2xS0TaOc0bLdlLaoT3BlbkFJl6Gn4w9f9kweuoccRksI"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are now a professional experiment analyzer."},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            top_p=1,
            n=1,
        )

        gpt_response = response.choices[0].message['content'].strip()
        return jsonify(gpt_response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_payload(request):
    for dm in ('odm', 'idm'):
        x = request.json.get(dm)
        if not x.get('name'):
            return 'Program name is required', 'dm', 400
        if 'dfs' not in x:
            msg = 'device feature list is for {} is required'.format(dm)
            return msg, 'df', 400

    unit_list = [name for name in chain(*Unit.query.values(Unit.name))]
    fn_list = [fn['fn_name'] for fn in ag_ccmapi(current_user.id, 'function.list')
               if (fn['fn_name'] not in ['all', 'x4', 'x5'])]
    iv_list = request.json['iv_list']
    sm_sensor = ['Acceleration', 'Gyroscope', 'Magnetometer', 'Orientation']
    morsensor = ['Alcohol', 'Humidity', 'UV']
    cyber_var_names = {}

    for iv in iv_list:
        cyber_var_names[iv['giv_name']] = iv['giv_name']
        for p in iv['params']:
            # check unit is not empty
            if p['unit'] not in unit_list:
                msg = 'Unit cannot be empty'
                return msg, 'df', 400

            # check invalid chars
            if p['device'] == 'Input Box':
                if p['type'] == 'string' and (
                        type(p['default']) != str or p['default'].find("'", 1, len(p['default'])-1) != -1
                        or '"' in p['default'] or "\\" in p['default']):
                    msg = 'default should not contain \', \", or \\ '
                    return msg, 'df', 400
            # check min, max is not empty if this field exists
            if p['device'] == 'Range Slider':
                try:
                    _min = float(p['min'])
                    _max = float(p['max'])
                    if p['default'] is bool:
                        raise ValueError()
                    _default = float(p['default'])
                except ValueError:
                    msg = 'min, max, and default should have value'
                    return msg, 'df', 400
                for x in ('min', 'max', 'default'):
                    if p[x] == "":
                        msg = '{} cannot be empty'.format(x)
                        return msg, 'df', 400
                # check if parameter value is reasonable
                if _min > _max:
                    msg = 'min value should be <= max value'
                    return msg, 'df', 400
                if _max < _default or _default < _min:
                    msg = 'default value should be between min and max'
                    return msg, 'df', 400

            # check function is not empty
            if p['device'] == 'Smartphone' and p['function'] not in fn_list:
                msg = 'Function cannot be empty'
                return msg, 'df', 400

            # check sensor is not empty
            if p['device'] == 'Smartphone' and p['sensor'] not in sm_sensor:
                msg = 'Sensor cannot be empty'
                return msg, 'df', 400

            if p['device'] == 'Morsensor' and p['sensor'] not in morsensor:
                msg = 'Sensor cannot be empty'
                return msg, 'df', 400

    # check odm_name is eng+number only
    odm_name = request.json['odm']['name']
    if re.match('^[a-zA-Z][a-zA-Z0-9]*$', odm_name) is None:
        return 'Invalid program name, english alphabet or number only', 'dm', 400

    # check actuator vars
    if request.json.get('output_variables'):
        msg = check_output_variables(request.json['output_variables'], cyber_var_names)
        if msg:
            return msg, 'actuator', 400

    return '', '', 200