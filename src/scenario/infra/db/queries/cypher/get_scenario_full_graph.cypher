-- src/scenario/infra/db/queries/cypher/get_scenario_full_graph.cypher

SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (scenario_node:Scenario)
    WHERE scenario_node.id = $scenario_id
    OPTIONAL MATCH (scenario_node)-[:HAS_ACT]->(act_node:Act)
    OPTIONAL MATCH (act_node)-[:HAS_SEQUENCE]->(seq_node:Sequence)
    OPTIONAL MATCH (seq_node)-[:LOCATED_AT]->(loc_node:Location)
    OPTIONAL MATCH (seq_node)-[:HAS_ENTITY]->(entity_node:EntityTemplate)
    RETURN
        scenario_node.id as scenario_id,
        scenario_node.state_manager_id as state_manager_id,
        scenario_node.title as title,
        scenario_node.concept as concept,
        scenario_node.summary as summary,
        scenario_node.description as description,
        scenario_node.difficulty as difficulty,
        scenario_node.genre as genre,
        scenario_node.tags as tags,
        scenario_node.total_acts as total_acts,
        act_node.id as act_id, act_node.name as act_name, act_node.goal as act_goal,
        act_node.region_name as act_region_name, act_node.region_description as act_region_desc, act_node.exit_criteria as act_exit,
        seq_node.id as seq_id, seq_node.name as seq_name, seq_node.description as seq_desc,
        seq_node.goal as seq_goal, seq_node.sequence_type as seq_type,
        loc_node.id as loc_master_id, loc_node.name as loc_name, loc_node.theme as loc_theme, loc_node.description as loc_desc,
        entity_node.id as ent_id, entity_node.master_id as ent_master_id, entity_node.name as ent_name, entity_node.category as ent_cat,
        entity_node.description as ent_desc, entity_node.tags as ent_tags, entity_node.state as ent_state,
        entity_node.meta as ent_meta, entity_node.dropped_items as ent_drops
$$::cstring, $1::agtype) as (
    scenario_id agtype, state_manager_id agtype, title agtype, concept agtype, summary agtype, description agtype,
    difficulty agtype, genre agtype, tags agtype, total_acts agtype,
    act_id agtype, act_name agtype, act_goal agtype,
    act_region_name agtype, act_region_desc agtype, act_exit agtype,
    seq_id agtype, seq_name agtype, seq_desc agtype, seq_goal agtype, seq_type agtype,
    loc_master_id agtype, loc_name agtype, loc_theme agtype, loc_desc agtype,
    ent_id agtype, ent_master_id agtype, ent_name agtype, ent_cat agtype, ent_desc agtype,
    ent_tags agtype, ent_state agtype, ent_meta agtype, ent_drops agtype
);
