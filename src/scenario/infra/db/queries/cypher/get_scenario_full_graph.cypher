-- src/scenario/infra/db/queries/cypher/get_scenario_full_graph.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})
    OPTIONAL MATCH (s)-[:HAS_ACT]->(a:Act)
    OPTIONAL MATCH (a)-[:HAS_SEQUENCE]->(seq:Sequence)
    OPTIONAL MATCH (seq)-[:LOCATED_AT]->(l:Location)
    OPTIONAL MATCH (seq)-[:HAS_ENTITY]->(e:EntityTemplate)
    RETURN
        s.id as scenario_id,
        s.title as title,
        s.concept as concept,
        s.summary as summary,
        s.description as description,
        s.difficulty as difficulty,
        s.genre as genre,
                s.tags as tags,
                s.total_acts as total_acts,
                a.id as act_id, a.name as act_name, a.goal as act_goal,
                a.region_name as act_region_name, a.region_description as act_region_desc, a.exit_criteria as act_exit,
                seq.id as seq_id, seq.name as seq_name, seq.description as seq_desc,

        seq.goal as seq_goal, seq.sequence_type as seq_type,
        l.id as loc_master_id, l.name as loc_name, l.theme as loc_theme, l.description as loc_desc,
        e.id as ent_id, e.master_id as ent_master_id, e.name as ent_name, e.category as ent_cat,
        e.description as ent_desc, e.tags as ent_tags, e.state as ent_state,
        e.meta as ent_meta, e.dropped_items as ent_drops
$$, $1) as (
    scenario_id agtype, title agtype, concept agtype, summary agtype, description agtype,
    difficulty agtype, genre agtype, tags agtype, total_acts agtype,
    act_id agtype, act_name agtype, act_goal agtype,
    act_region_name agtype, act_region_desc agtype, act_exit agtype,
    seq_id agtype, seq_name agtype, seq_desc agtype, seq_goal agtype, seq_type agtype,
    loc_master_id agtype, loc_name agtype, loc_theme agtype, loc_desc agtype,
    ent_id agtype, ent_master_id agtype, ent_name agtype, ent_cat agtype, ent_desc agtype,
    ent_tags agtype, ent_state agtype, ent_meta agtype, ent_drops agtype
);
