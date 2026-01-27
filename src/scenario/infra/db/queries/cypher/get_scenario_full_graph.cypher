-- src/scenario/infra/db/queries/cypher/get_scenario_full_graph.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})
    OPTIONAL MATCH (s)-[:HAS_ACT]->(a:Act)
    OPTIONAL MATCH (a)-[:HAS_SEQUENCE]->(seq:Sequence)
    OPTIONAL MATCH (seq)-[:LOCATED_AT]->(l:Location)
    OPTIONAL MATCH (seq)-[:HAS_ENTITY]->(e:EntityTemplate)
    RETURN
        s.concept as concept,
        s.summary as summary,
        a.id as act_id, a.name as act_name,
        seq.id as seq_id, seq.name as seq_name,
        l.name as loc_name, l.theme as loc_theme,
        e.id as ent_id, e.name as ent_name, e.category as ent_cat,
        e.description as ent_desc, e.interaction_guide as ent_guide,
        e.disposition as ent_disp, e.occupation as ent_occ, e.dialogue_style as ent_dial,
        e.item_type as ent_itype, e.grade as ent_grade,
        e.base_difficulty as ent_diff, e.combat_description as ent_combat
$$, $1) as (
    concept agtype, summary agtype, act_id agtype, act_name agtype,
    seq_id agtype, seq_name agtype, loc_name agtype, loc_theme agtype,
    ent_id agtype, ent_name agtype, ent_cat agtype, ent_desc agtype,
    ent_guide agtype, ent_disp agtype, ent_occ agtype, ent_dial agtype,
    ent_itype agtype, ent_grade agtype, ent_diff agtype, ent_combat agtype
);
