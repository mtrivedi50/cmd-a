previous_migration=$(ls -t alembic/versions | grep -v '__pycache__' | head -n 1)
uv run alembic revision --autogenerate;
sleep 1

migration=$(ls -t alembic/versions | grep -v '__pycache__' | head -n 1)
if [[ "$previous_migration" != "$migration" ]]; then
    echo ""
    echo "Importing sqlmodel in new migration file: ${migration}"
    sed -i '' '11i\
import sqlmodel
    ' alembic/versions/$migration
    echo "Done!"
fi
