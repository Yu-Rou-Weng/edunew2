SED_CMD=sed -i
CP_CMD=cp -n

ENVFILE=./.env
IOTTALK_INI_SAMPLE=./iottalk/conf/iottalk.ini.sample
AG_ENV_SAMPLE=./iottalk/conf/autogen_env.example
EDUTALK_INI_SAMPLE=./edutalk/edutalk.ini.sample

all: envfile
	git submodule init
	git submodule update --recursive
	docker-compose build

envfile:
	if [ ! -s ${ENVFILE} ]; then echo COMPOSE_PROJECT_NAME=${USER}-iottalk > ${ENVFILE}; fi

config:
	# iottalk config
	docker run --name tmp-iottalk -d iottalk:${USER}
	docker cp tmp-iottalk:/iottalk/conf/iottalk.ini ${IOTTALK_INI_SAMPLE}
	docker rm -f tmp-iottalk
	# post-patch
	${SED_CMD} -e 's/# userdir = .*$$/userdir = \/iottalk\/data/'  ${IOTTALK_INI_SAMPLE}
	${SED_CMD} -e 's/# redis-host = localhost/redis-host = redis/' ${IOTTALK_INI_SAMPLE}
	${CP_CMD} ${IOTTALK_INI_SAMPLE} $(patsubst %.sample,%,${IOTTALK_INI_SAMPLE})

	# iottalk autogen config
	docker run --name tmp-autogen -d autogen:${USER}
	docker cp tmp-autogen:/iottalk-autogen/_/env/.env.example ${AG_ENV_SAMPLE}
	docker rm -f tmp-autogen
	# post-patch
	${SED_CMD} -e 's/<your_secret_key>/'$$(tr -dc A-Za-z0-9 </dev/urandom | head -c 20)'/' ${AG_ENV_SAMPLE}
	${SED_CMD} -e 's@USER_DIR=""@USER_DIR="/"@' ${AG_ENV_SAMPLE}
	${CP_CMD} ${AG_ENV_SAMPLE} $(patsubst %.example,%,${AG_ENV_SAMPLE})

	# mosquitto config
	docker run --name tmp-mosquitto -d eclipse-mosquitto:2.0.10
	docker cp tmp-mosquitto:/mosquitto/config/mosquitto.conf ./mosquitto/mosquitto.conf.sample
	docker rm -f tmp-mosquitto

	# nginx config
	docker run --name tmp-nginx -d nginx:1.15.11-alpine
	docker cp tmp-nginx:/etc/nginx/nginx.conf ./nginx/nginx.conf.sample
	docker rm -f tmp-nginx

	# edutalk config
	docker run --name tmp-edutalk -d edutalk:${USER}
	docker cp tmp-edutalk:/edutalk/edutalk.ini  ${EDUTALK_INI_SAMPLE}
	docker rm -f tmp-edutalk
	# post-patch
	${SED_CMD} -e 's/# userdir = .*$$/userdir = \/edutalk/'  ${EDUTALK_INI_SAMPLE}
	${SED_CMD} -e 's/secret_key = dev/secret_key = '$$(tr -dc A-Za-z0-9 </dev/urandom | head -c 20)'/' ${EDUTALK_INI_SAMPLE}
	${SED_CMD} -e 's/es_password = dev/es_password = '$$(tr -dc A-Za-z0-9 </dev/urandom | head -c 20)'/' ${EDUTALK_INI_SAMPLE}
	${CP_CMD} ${EDUTALK_INI_SAMPLE} $(patsubst %.sample,%,${EDUTALK_INI_SAMPLE})

up:
	git -C iottalk-core        checkout master
	git -C iottalk-core        pull
	git -C iottalk-classic-gui checkout master
	git -C iottalk-classic-gui pull
	git -C iottalk-autogen     checkout master
	git -C iottalk-autogen     pull
	git -C edutalk-server      checkout v2-classic
	git -C edutalk-server      pull

initdb:
	docker-compose up -d
	docker-compose exec ccm iotctl -c /iottalk/conf/iottalk.ini initdb ccm
	docker-compose exec autogen python manage.py migratesites
	docker-compose exec edutalk edutalk -c /edutalk/edutalk.ini initdb
	docker-compose down

reboot:
	docker-compose down
	docker-compose up -d
	docker-compose exec autogen python manage.py migratesites
