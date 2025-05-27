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
  SOLUTIONS_REPO=https://github.com/openimis/solutions.git
  SOLUTIONS_PATH=$FIXTURE_PATH/solutions
  FLATTENED_FIXTURES_PATH=$SOLUTIONS_PATH/fixtures

  # Clone solutions repo if missing
  if [ ! -d "$SOLUTIONS_PATH" ]; then
    echo "Cloning openIMIS solutions repo..."
    mkdir -p "$FIXTURE_PATH"
    git clone --depth 1 "$SOLUTIONS_REPO" "$SOLUTIONS_PATH"
  fi

  # Flatten all fixture files into one folder
  echo "Collecting and flattening fixture files..."
  mkdir -p "$FLATTENED_FIXTURES_PATH"
  find "$SOLUTIONS_PATH" -type f -path "*/fixtures/*.json" ! -name "roles-right.json" | while read -r f; do
    cp "$f" "$FLATTENED_FIXTURES_PATH/$(basename "$f")"
  done

  if [[ "$FIXTURE_INIT" == "true" ]]; then
    echo "Fixture init enabled..."
    for fixture in "$FLATTENED_FIXTURES_PATH"/*.json; do
      name=$(basename "$fixture" .json)
      echo "Checking if table for fixture '$name' is empty..."
      count=$(python manage.py dumpdata "$name" 2>/dev/null | jq length || echo 0)
      if [[ "$count" -eq 0 ]]; then
        echo "Loading fixture: $fixture"
        python manage.py loaddata "$fixture"
      else
        echo "Skipping $name: table not empty."
      fi
    done
  fi

  echo "Loading roles-rights fixture with foreign key support..."
  python manage.py load_fixture_foreign_key "$FLATTENED_FIXTURES_PATH/roles-right.json" uuid
}

init() {
  if [ "${DJANGO_MIGRATE,,}" == "true" ] || [ -z "$SCHEDULER_AUTOSTART" ]; then
    echo "Running Django migrations..."
    python manage.py migrate
    export SCHEDULER_AUTOSTART=True
    load_fixtures_if_needed
  fi
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
