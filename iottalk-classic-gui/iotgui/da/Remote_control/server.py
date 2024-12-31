import atexit
import iot.dan
import os

from flask import Flask, render_template, request

HOST = '0.0.0.0'
PORT = 7789

app = Flask(__name__)
connect_df = []


def on_data(*args):
    print('data:', args)
    return True


def on_signal(signal, df_list):
    global connect_df
    print('signal:', signal, df_list)
    if 'CONNECT' == signal:
        for df in df_list:
            if df not in connect_df:
                connect_df.extend(df_list)
                connect_df = sorted(connect_df)
    elif 'DISCONNECT' == signal:
        for df in df_list:
            connect_df.remove(df)
    elif 'SUSPEND' == signal:
        # Not use
        pass
    elif 'RESUME' == signal:
        # Not use
        pass
    return True


def on_exit():
    iot.dan.deregister()


@app.route('/')
def mail_page():
    global connect_df
    return render_template('index.html', connect_df=connect_df)


@app.route('/<df>', methods=['POST'])
def get_push(df):
    data = request.json
    print(data)
    iot.dan.push(df, data)
    return '', 200


if '__main__' == __name__:
    idf_list = []
    idf_list.append(['PPT_Control', ['num', 'num', 'num']])
    for i in range(1, 10):
        idf_list.append(['Keypad{}'.format(i), ['num']])
        idf_list.append(['Button{}'.format(i), ['num']])
        idf_list.append(['Switch{}'.format(i), ['num']])
        idf_list.append(['Knob{}'.format(i), ['num']])
        idf_list.append(['Color-I{}'.format(i), ['num', 'num', 'num']])

    context = iot.dan.register(
        os.environ.get('CSM_URL', 'http://localhost:9992'),
        on_signal=on_signal,
        on_data=on_data,
        accept_protos=['mqtt'],
        idf_list=idf_list,
        name='RM-test',
        profile={'model': 'Remote_control'},
    )

    atexit.register(on_exit)

    app.run(
        host=HOST,
        port=PORT,
        threaded=True,
    )
