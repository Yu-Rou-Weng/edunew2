import json
import logging

from datetime import timedelta
from functools import wraps


from django.conf import settings
from django.contrib import auth
from django.db import transaction
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views import View

from .manage import sync_project, update_dfos, update_execution
from .color import SimTalkColor
from .models import (
    AccessToken,
    DeviceObject,
    Distribution,
    Project,
    RefreshToken,
    SimStatus,
    User,
)
from .utils import (
    security_redirect,
    stop_simulator,
    test_ag_login,
    test_ag_oauth2,
    update_ccm_simulation,
    oauth2_client,
)

log = logging.getLogger(SimTalkColor.wrap(SimTalkColor.logger, 'SIMTALK.views'))
log.setLevel(level=logging.INFO)


def login_required(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):

        def redirect_login():
            next_page = request.get_full_path()

            if settings.OAUTH2_CLIENT_ID:
                # Use OAuth url
                login_url = reverse('auth')
            else:
                # Use Tradition login url
                login_url = reverse('login', kwargs={'u_id': u_id})

            # If the session has old user data, clear it
            request.session['u_id'] = None

            return redirect(f'{login_url}?next={next_page}')

        u_id = self.kwargs['u_id']
        user = User.objects.filter(u_id=u_id).first()

        if not user:
            log.error('User credential does not match.')
            return redirect_login()

        if request.session.get('u_id') != u_id:
            log.error('User credential does not match: session u_id=%s, u_id=%s.',
                      request.session.get('u_id'), u_id)
            return redirect_login()

        if settings.OAUTH2_CLIENT_ID:
            # Use OAuth, check access token is still valid
            accesstoken_record = (
                AccessToken.objects.filter(user_id=u_id).latest("id")
            )
            if not accesstoken_record:
                # There is no access token.
                return redirect_login()

            if u_id != test_ag_oauth2(accesstoken_record.token):
                # Access token is invalid. Out-of-date, user mismatch, etc.
                return redirect_login()
        else:
            # Use tradition account, check username/password are still valid.
            if u_id != test_ag_login(user.username, user.password):
                return redirect_login()

        return func(self, request, *args, **kwargs)

    return wrapper


class IndexView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('Unknown page.')


class LoginView(View):
    template_name = 'simtalk/login.html'

    def _render(self, request, message=''):
        return render(
            request,
            self.template_name,
            {
                'WEB_SERVER_PREFIX': settings.WEB_SERVER_PREFIX,
                'message': message
            }
        )

    def get(self, request, *args, **kwargs):
        if settings.OAUTH2_CLIENT_ID:
            return redirect(reverse('auth', kwargs={"next": request.GET.get('next', '/')}))

        return self._render(request)

    def post(self, request, *args, **kwargs):
        if settings.OAUTH2_CLIENT_ID:
            return redirect(reverse('auth', kwargs={"next": request.GET.get('next', '/')}))

        u_id = self.kwargs['u_id']
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            # Test ths username/password in IoTtalk tradition account
            iottalk_u_id = test_ag_login(username, password)
        except Exception as e:
            log.error(e)
            return HttpResponse("AG CCMAPI failed, please contact the administrator.")

        # Check iottalk u_id is valid and match.
        if u_id != iottalk_u_id:
            log.info('%s login failed. %s != %s', username, u_id, iottalk_u_id)
            request.session['u_id'] = None
            return self._render(request, 'Login failed.')

        # Update or Create the user information.
        user_record, _ = User.objects.update_or_create(
            u_id=u_id,
            defaults={
                'username': username,
                'password': password
            },
        )
        request.session['u_id'] = u_id
        log.info('%s login successful.', username or 'Unknown user')
        return security_redirect(request.GET.get('next'))


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        if settings.OAUTH2_CLIENT_ID:
            # TODO
            pass

        auth.logout(request)
        log.info('%s logout.', request.user.username or 'Unknown user')
        return HttpResponse("You are logged out.")


class AuthView(View):
    http_method_names = [
        'get',
    ]

    def get(self, request, *args, **kwargs):
        next_page = request.GET.get('next')
        if request.user.is_authenticated:
            # Redirect a user to the next page if he/she already logs in
            return security_redirect(next_page)

        # Redirect a user to the authorization endpoint
        #
        # Ref: https://docs.authlib.org/en/stable/client/frameworks.html#id1
        return oauth2_client.iottalk.authorize_redirect(
            request,
            redirect_uri=settings.OAUTH2_REDIRECT_URI,
            state=next_page,
        )


class AuthCallbackView(View):
    http_method_names = [
        'get',
    ]

    def get(self, request, *args, **kwargs):
        next_page = request.GET.get('state', reverse('index'))
        # Check if a request has `code` query parameter
        if not request.GET.get('code'):
            # Redirect a user to the index page if he/she already logs in
            if request.session.get('u_id'):
                return redirect(next_page)

            # Redirect a user to the authorization endpoint
            return oauth2_client.iottalk.authorize_redirect(
                request,
                redirect_uri=settings.OAUTH2_REDIRECT_URI,
                state=next_page,
            )

        try:
            # Exchange access token with an authorization code with token endpoint
            #
            # Ref: https://docs.authlib.org/en/stable/client/frameworks.html#id1
            token_response = oauth2_client.iottalk.authorize_access_token(request)

            # Parse the received ID token
            user_info = oauth2_client.iottalk.parse_id_token(request, token_response)
        except Exception:
            log.exception('authorize access token fail.')

            return HttpResponse('Something broken...')

        u_id = test_ag_oauth2(token_response.get('access_token'))
        if not u_id:
            log.error("Can't find user data in IoTtalk. ")
            return HttpResponseBadRequest("Can't find user data in IoTtalk.")

        try:
            with transaction.atomic():
                # Use the sub parameter value in the ID token to get an existing user or
                # create a new user.
                user_record, _created = User.objects.update_or_create(
                    u_id=u_id,
                    defaults={
                        'sub': user_info.get('sub'),
                        'username': user_info.get('preferred_username', ''),
                        'email': user_info.get('email', ''),
                    }
                )

                # Get or create a refresh token object
                refresh_token_record, refresh_token_record_created = \
                    RefreshToken.objects.get_or_create(
                        user_id=u_id,
                        token=token_response.get('refresh_token', ''),
                    )

                # If a refresh token object exists and there is another refresh token
                # in the received token, it means the old refresh token should be replaced
                # with a new one.
                if not refresh_token_record_created and \
                        token_response.get('refresh_token'):
                    refresh_token_record.token = token_response.get('refresh_token')
                    refresh_token_record.save()

                # Save a received access token in the database
                AccessToken.objects.create(
                    user_id=u_id,
                    token=token_response.get('access_token'),
                    refresh_token_id=refresh_token_record.id,
                    expires_at=(
                        timezone.now()
                        + timedelta(seconds=token_response.get('expires_in', 0))
                    )
                )
        except Exception as e:
            log.error("%s authenticate failed.", user_info.get('preferred_username'))
            log.error(e)
            return HttpResponseBadRequest(
                "Save credential failed, please contact administrator."
            )

        # Login an user manually
        request.session['u_id'] = u_id
        log.info('%s login successful.', user_record.username or 'Unknown user')

        return redirect(next_page)


class ExecutionView(View):  # TODO: change to use u_id
    template_name = 'simtalk/execution.html'

    @login_required
    def get(self, request, *args, **kwargs):
        '''get project simulation info

        context = {
            'p_name': project.p_name,
            'p_id': project.p_id,
            'u_id': project.u_id,
            'sim': project.sim,
            'do_list':  [
                {
                    'do_id': 1,
                    'dm_name': 'Ball-Slid',
                    'sim': False,
                    'is_default': True
                },
                ...
            ],
        }
        '''
        p_id = self.kwargs['p_id']
        u_id = request.session['u_id']
        log.debug('Execution.GET: p_id: %s, u_id: %s', p_id, u_id)

        # First, synchronize the project from CCM
        try:
            sync_project(p_id, u_id)
        except Exception as e:
            return HttpResponseBadRequest(e)

        # Senconde, Query Project
        project_record = Project.objects.filter(p_id=p_id).first()

        # if something wrong
        if not project_record:
            msg = 'Project (p_id={}) not found.'.format(p_id)
            log.error(msg)
            return HttpResponseBadRequest(msg)

        # Third, fetch all relative data and change to dict
        context = project_record.to_dict()
        context.update({'WEB_SERVER_PREFIX': settings.WEB_SERVER_PREFIX})

        return render(request, self.template_name, context)

    @login_required
    @method_decorator(csrf_protect)
    def put(self, request, *args, **kwargs):
        # Entry 2 - Fig 7 Save btn
        '''
        request = {
            'p_id': p_id,
            'sim': sim,
            'do_list':  [
                {'do_id': 1, 'sim': False},
                {'do_id': 2, 'sim': False},
                ...
            ],
        }
        '''
        p_id = self.kwargs['p_id']
        u_id = request.session['u_id']
        log.debug('Execution.PUT: p_id: %s, u_id: %s', p_id, u_id)

        do_infos = json.loads(request.body)
        log.debug(do_infos)

        # update execution status
        update_execution(p_id, u_id, do_infos)

        return HttpResponse('ok')

    # Make CSRF checks disabled on the token endpoint
    #
    # Cause the delete request will send from IoTtalk-GUI.
    #
    # Ref: https://tinyurl.com/6bjer9mv (csrf_exempt)
    # Ref: https://tinyurl.com/2p847buu (method_decorator)
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @login_required
    def delete(self, request, *args, **kwargs):
        # GUI simulation btn on -> off
        p_id = self.kwargs['p_id']
        u_id = request.session['u_id']
        project_record = Project.objects.get(p_id=p_id)
        if not project_record or project_record.u_id.u_id != u_id:
            log.error('Execution.Delete Failed: p_id: %s owner is not u_id: %s', p_id, u_id)
        else:
            log.debug('Execution.Delete: p_id: %s, u_id: %s', p_id, u_id)

        # Update DeviceObject records
        do_records = DeviceObject.objects.filter(p_id=p_id).all()
        for do_record in do_records:
            if do_record.ag_token:
                stop_simulator(do_record)

        # Update the Project status
        update_ccm_simulation(p_id, u_id, SimStatus.OFF)

        return HttpResponse('ok')


class SetupView(View):  # TODO: change to use u_id
    template_name = 'simtalk/setup.html'

    @login_required
    def get(self, request, *args, **kwargs):
        '''get do info

        context = {
            "do_id": do_id,
            "dm_name": dm_name,
            "p_id": p_id,
            "dfo_list": [
                {
                    "dfo_id": dfo_id,
                    "df_name": df_name,
                    "value_distribution": [
                        {
                            "v_id": v_id,
                            "name": distribution,
                            "param_i": param_i,
                            "mean": mean,
                            "var": var,
                            "seed": seed,
                            "min": min,
                            "max": max,
                        },
                        ...
                    ],
                    "time_distribution": {
                        "name": t.distribution,
                        "mean": t.mean,
                        "var": t.var,
                        "seed": t.seed
                    }
                }
            ],

        }
        '''
        u_id = request.session['u_id']
        p_id = self.kwargs['p_id']
        do_id = self.kwargs['do_id']
        log.debug('Setup.GET: p_id: %s\tdo_id: %s', p_id, do_id)

        # First, synchronize the project from CCM
        try:
            sync_project(p_id, u_id)
        except Exception as e:
            return HttpResponseBadRequest(e)

        # Senconde, Query DeviceObject
        do_record = DeviceObject.objects.filter(do_id=do_id).first()

        # if something wrong
        if not do_record:
            msg = 'DO (do_id={}) not found.'.format(do_id)
            log.error(msg)
            return HttpResponseBadRequest(msg)

        # Third, fetch all relative data and change to dict
        context = do_record.to_dict()

        # Fourth, append distribution_options to context
        context.update({'distribution_options': Distribution.to_dict()})
        context.update({'WEB_SERVER_PREFIX': settings.WEB_SERVER_PREFIX})

        return render(request, self.template_name, context)

    @login_required
    def put(self, request, *args, **kwargs):
        ''' update do info

        request.body: [
            {
                "dfo_id": 1,
                "df_name": "Gravity",
                "value_distribution": [
                    {
                        "id": id,
                        "dfo_id": dfo_id,
                        "distribution": "NO",
                        "param_i": 0,
                        "param_type" "float",
                        "mean": 10000,
                        "var": 2000,
                        "seed": 141424,
                        "min": 0,
                        "max": 10
                    },
                    ...
                ],
                "time_distribution": {
                    "distribution":"NO",
                    "mean":50000,
                    "var":20000,
                    "seed":357323
                }
            },
            ...
        ]

        response: 'ok'
        '''
        p_id = self.kwargs['p_id']
        do_id = self.kwargs['do_id']
        log.debug('Setup.GET: p_id: %s\tdo_id: %s', p_id, do_id)

        dfo_infos = json.loads(request.body)
        log.debug(dfo_infos)

        # update data
        result = update_dfos(do_id, dfo_infos)

        # if something wrong
        if result is not True:
            return HttpResponseBadRequest(json.dumps(result))

        return HttpResponse('ok')
