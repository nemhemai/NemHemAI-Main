# Graph Schema Design

## Nodes

### Act
Properties:
- act_id (Primary Key)
- name

### Section
Properties:
- section_id (Primary Key)
- act_id (Foreign reference)
- title
- content

## Relationships

(:Act)-[:HAS_SECTION]->(:Section)

(:Section)-[:REFERENCES]->(:Section)