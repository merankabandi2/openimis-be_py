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

  SOLUTION_NAME="${FIXTURE_SOLUTION:-coreMIS}"

  # Configuration
  FIXTURE_PATH="./initialization"
  SOLUTION_PATH="$FIXTURE_PATH/$SOLUTION_NAME"
  FIXTURE_DIR="$SOLUTION_PATH/fixtures"
  
  echo "=== Fixture loading test for solution: $SOLUTION_NAME ==="

  # Clone if solution folder doesn't exist
  if [ ! -d "$SOLUTION_PATH" ]; then
    echo "Cloning openIMIS solutions repo and extracting '$SOLUTION_NAME'..."
    mkdir -p "$FIXTURE_PATH"
    git clone --depth 1 https://github.com/openimis/solutions.git "$FIXTURE_PATH/tmp_solutions"

    if [ ! -d "$FIXTURE_PATH/tmp_solutions/$SOLUTION_NAME" ]; then
      echo "Solution '$SOLUTION_NAME' not found in solutions repo."
      exit 2
    fi

    mv "$FIXTURE_PATH/tmp_solutions/$SOLUTION_NAME" "$SOLUTION_PATH"
    rm -rf "$FIXTURE_PATH/tmp_solutions"
  fi

  # Load all fixtures (except roles-right.json)
  FIXTURE_FILES=$(find "$FIXTURE_DIR" -type f -name "*.json" ! -name "roles-right.json")

  for f in $FIXTURE_FILES; do
    name=$(basename "$f" .json)
    echo "Checking if table for fixture '$name' is empty..."
    count=$(python manage.py dumpdata "$name" 2>/dev/null | jq length || echo 0)

    if [[ "$count" -eq 0 ]]; then
      echo "Loading fixture: $f"
      python manage.py loaddata "$f"
    else
      echo "Skipping $name: table not empty."
    fi
  done

  # Load roles-right fixture
  if [ -f "$FIXTURE_DIR/roles-right.json" ]; then
    echo "Loading roles-right fixture with foreign key support..."
    python manage.py load_fixture_foreign_key "$FIXTURE_DIR/roles-right.json" uuid
  else
    echo "roles-right.json not found in $FIXTURE_DIR. Skipping."
  fi

  echo "=== Fixture test complete for $SOLUTION_NAME ==="
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
