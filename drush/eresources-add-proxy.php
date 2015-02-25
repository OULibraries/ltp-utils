<?php
// Get all nodes of 'ereference' and 'databases' type, populate the proxy field with a value of '1' if there is no field currently.
$eresource = db_query("SELECT nid, vid, type FROM {node} WHERE type = 'ereference' OR type = 'databases'")->fetchAllAssoc('nid');

foreach ($eresource as $nid => $values) {
    $key = array(
      'entity_id' => $values->nid,
    );
    // fields based on existing nodes
    $fields = array(
      'entity_type' => 'node',
      'bundle' => $values->type,
      'deleted' => 0,
      'entity_id' => $values->nid,
      'revision_id' => $values->vid,
      'language' => 'und',
      'delta' => 0,
      'field_proxy_value' => '1',
    );
    // only insert missing fields, don't update existing fields.
    db_merge('field_data_field_proxy')
      ->key($key)
      ->insertFields($fields)
      ->execute();
    db_merge('field_revision_field_proxy')
      ->key($key)  
      ->insertFields($fields)
      ->execute();
      
    // Save fields, use actual node object
    $node = node_load($values->nid);
    field_attach_presave('node', $node);
    field_attach_update('node', $node);
    entity_get_controller('node')->resetCache($key);
}
?>
