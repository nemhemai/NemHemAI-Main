# run_once_constraints.py

from connection import driver
from queries import create_constraints

with driver.session() as session:
    session.execute_write(create_constraints)

print("Constraints ensured.")