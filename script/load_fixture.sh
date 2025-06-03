#!/bin/bash
set -e

# Use env var or default to 'openimis'
SOLUTION_NAME="${FIXTURE_SOLUTION:-openIMIS}"

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

for fixture_file in "$FIXTURE_DIR"/*.json; do
  name=$(basename "$fixture_file")
  model=$(jq -r '.[0].model' "$fixture_file" 2>/dev/null)

  if [[ -z "$model" || "$model" == "null" ]]; then
    echo "⚠️  Skipping $name: couldn't determine model."
    continue
  fi

  echo "🔍 Checking model: $model from $name"

  count=$(python ../openIMIS/manage.py shell -c "from ${model%.*} import ${model#*.} as M; print(M.objects.count())" 2>/dev/null || echo 0)

  if [[ "$count" -eq 0 ]]; then
    echo "✅ Loading fixture: $fixture_file"
    python ../openIMIS/manage.py loaddata "$fixture_file"
  else
    echo "⏩ Skipping $model ($name): table not empty ($count records)."
  fi
done

# Load roles-right fixture
if [ -f "$FIXTURE_DIR/roles-right.json" ]; then
  echo "Loading roles-right fixture with foreign key support..."

  echo "Checking if table for fixture RoleRight is empty"
  count=$(python ../openIMIS/manage.py shell -c "from core import RoleRight as M; print(M.objects.count())" 2>/dev/null || echo 0)

  if [[ "$count" -eq 0 ]]; then
    echo "Loading roles-right.json fixture..."
    python ../openIMIS/manage.py load_fixture_foreign_key "$FIXTURE_DIR/roles-right.json" --field name
  else
    echo "Skipping roles-right.json: RoleRight table not empty ($count records)."
  fi
else
  echo "roles-right.json not found in $FIXTURE_DIR. Skipping."
fi

echo "=== Fixture test complete for $SOLUTION_NAME ==="
