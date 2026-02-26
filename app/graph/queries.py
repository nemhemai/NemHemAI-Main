def upsert_act(tx, act_id, act_title):
    tx.run("""
        MERGE (a:Act {act_id: $act_id})
        ON CREATE SET a.name = $act_title
    """, act_id=act_id, act_title=act_title)


def upsert_section(tx, section_data):
    tx.run("""
        MERGE (s:Section {section_id: $section_id})
        ON CREATE SET
            s.title = $title,
            s.content = $content,
            s.act_id = $act_id
    """,
        section_id=section_data["section_id"],
        title=section_data["heading"],
        content=section_data["content"],
        act_id=section_data["act_id"]
    )


def create_has_section(tx, act_id, section_id):
    tx.run("""
        MATCH (a:Act {act_id: $act_id})
        MATCH (s:Section {section_id: $section_id})
        MERGE (a)-[:HAS_SECTION]->(s)
    """, act_id=act_id, section_id=section_id)