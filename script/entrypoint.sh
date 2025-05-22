#!/bin/bash
set -e

show_help() {
  echo """
  Commands
  ---------------------------------------------------------------
  start            : start django
  worker           : start Celery worker
  start_asgi       : use daphne -b ASGI_IP:WSGI_PORT -p SERVER_PORT  ASGI_APPLICATION
  start_wsgi       : use gunicorn -b WSGI_IP:WSGI_PORT -w WSGI_WORKERS WSGI_APPLICATION
  manage           : run django manage.py
  eval             : eval shell command
  bash             : run bash
  """
}

load_fixtures_if_needed() {
  echo "Checking and loading optional fixtures..."

  FIXTURE_PATH=/openimis-be/initialization
  SOLUTIONS_PATH=$FIXTURE_PATH/solutions

  if [ ! -d "$SOLUTIONS_PATH" ]; then
    echo "Cloning openIMIS solutions repo..."
    mkdir -p "$FIXTURE_PATH"
    git clone --depth 1 https://github.com/openimis/solutions.git "$SOLUTIONS_PATH"
  fi

  if [[ "$FIXTURE_INIT" == "true" ]]; then
    echo "Fixture init enabled..."

    FIXTURE_SETS=(
      "coreMIS/fixtures/locations.json"
      "coreMIS/fixtures/education.json"
      "coreMIS/fixtures/health_facilities.json"
      "sphf/fixtures/sphf_indicator.json"
    )

    for f in "${FIXTURE_SETS[@]}"; do
      name=$(basename "$f" .json)
      echo "Checking if table for fixture $name is empty..."
      count=$(python manage.py dumpdata "$name" 2>/dev/null | jq length || echo 0)
      if [[ "$count" -eq 0 ]]; then
        echo "Loading fixture: $f"
        python manage.py loaddata "$SOLUTIONS_PATH/$f"
      else
        echo "Skipping $name: table not empty."
      fi
    done
  fi

  echo "Loading roles-right with foreign key support..."
  python manage.py load_fixture_foreign_key "$SOLUTIONS_PATH/coreMIS/fixtures/core/roles-right.json" uuid
}

init() {
  if [ "${DJANGO_MIGRATE,,}" == "true" ] || [ -z "$SCHEDULER_AUTOSTART" ]; then
    echo "Running Django migrations..."
    python manage.py migrate
    export SCHEDULER_AUTOSTART=True
  fi

  load_fixtures_if_needed
}

if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
  export DJANGO_SETTINGS_MODULE=openIMIS.settings
fi

case "$1" in
  "start" )
    init
    echo "Starting Django..."
    python server.py
  ;;
  "start_asgi" )
    init
    echo "Starting Django ASGI..."
    daphne -b "${ASGI_IP:-0.0.0.0}" -p "${ASGI_PORT:-8000}" "${ASGI_APPLICATION:-openIMIS.asgi:application}"
  ;;
  "start_wsgi" )
    init
    echo "Starting Django WSGI..."
    gunicorn -b "${WSGI_IP:-0.0.0.0}:${WSGI_PORT:-8000}" -w "${WSGI_WORKERS:-4}" "${WSGI_APPLICATION:-openIMIS.wsgi}"
  ;;
  "worker" )
    echo "Starting Celery with url ${CELERY_BROKER_URL} ${DB_NAME}..."
    echo "Settings module: $DJANGO_SETTINGS_MODULE"
    celery -A openIMIS worker --loglevel=DEBUG
  ;;
  "manage" )
    ./manage.py "${@:2}"
  ;;
  "eval" )
    eval "${@:2}"
  ;;
  "bash" )
    bash
  ;;
  * )
    show_help
  ;;
esac
