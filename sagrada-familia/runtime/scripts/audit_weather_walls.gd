extends SceneTree
## Read-only integration probe. This does not move or constrain the visitor.
## Build the production collider graph and cast real physics rays at two walls.

func _initialize() -> void:
 call_deferred("_audit")

func _audit() -> void:
 var builder = load("res://scripts/collision_builder.gd")
 var source_path := ProjectSettings.globalize_path("res://../build/colliders.json")
 var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(source_path))
 var scene := Node3D.new()
 root.add_child(scene)
 var metadata: Dictionary = builder.build(scene,data)
 await physics_frame
 await physics_frame
 var checks: Array[Dictionary] = []
 for label in ["Nativity","Passion"]:
  var source_name: String = label+"_inner_weather_backing_above_entrance_clearance"
  var side: float = -1.0 if label=="Nativity" else 1.0
  var record: Dictionary = {}
  for item in data.get("colliders",[]):
   if item.get("name","")==source_name:
    record=item
    break
  var details := {"name":source_name,"passed":false,"method":"production collider shape plus physics ray; not a flight movement test"}
  if not record.is_empty():
   var center: Array = record.center
   var size: Array = record.size
   var expected_center := Vector3(52.5,20.25,-side*29.85)
   var converted: Vector3 = builder.v3(center)
   var dimensions := Vector3(float(size[0]),float(size[2]),float(size[1]))
   var start := Vector3(52.5,18.0,-side*33.85)
   var end := Vector3(52.5,18.0,-side*25.85)
   var hit := scene.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(start,end,1))
   var matched: bool = not hit.is_empty() and str(hit.collider.get_meta("source_name",""))==source_name
   var hit_distance: float = start.distance_to(hit.position) if not hit.is_empty() else -1.0
   details["passed"] = converted.distance_to(expected_center)<0.001 and dimensions.distance_to(Vector3(30,20.5,0.8))<0.001 and matched and absf(hit_distance-3.6)<0.005 and not bool(record.get("walkable_floor",false)) and not bool(record.get("flight_blocking",false))
   details["source_center_blender"] = center
   details["source_size_blender"] = size
   details["height_range_m"] = [float(center[2])-float(size[2])*0.5,float(center[2])+float(size[2])*0.5]
   details["ray_height_m"] = 18.0
   details["ray_distance_m"] = hit_distance
   details["expected_distance_m"] = 3.6
   details["matched_collider"] = matched
   details["hit_position_godot"] = [hit.position.x,hit.position.y,hit.position.z] if not hit.is_empty() else []
  checks.append(details)
 var passed := checks.size()==2
 for check in checks: passed=passed and bool(check.passed)
 var report := {"passed":passed,"collider_count":metadata.count,"colliders_sha256":FileAccess.get_sha256(source_path),"checks":checks,"inspection_flight":"Unchanged: authored walls do not constrain inspection flight; Jesus exclusion is unchanged."}
 var output := FileAccess.open("res://qa/upper_weather_wall_shapes_final.json",FileAccess.WRITE)
 output.store_string(JSON.stringify(report,"  ")+"\n")
 output.close()
 print("SAGRADA_WALL_SHAPE_AUDIT ",JSON.stringify(report))
 quit(0 if passed else 1)
