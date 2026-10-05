extends Node
## Diagnostics drive the production capsule programmatically.
## Browser/OS input, pointer lock and rendering are verified separately.
signal progress(report: Dictionary)
var app
var checks: Array[Dictionary] = []
var failures := 0

func _record(name: String, passed: bool, details: Dictionary = {}) -> void:
 checks.append({"name":name,"passed":passed,"details":details})
 if not passed: failures += 1
 progress.emit({"running":true,"current_test":name,"completed":checks.size(),"failures":failures})

func run(main) -> Dictionary:
 app = main
 var began := Time.get_ticks_msec()
 checks.clear()
 failures = 0
 app._pause()
 app.menu.hide()
 app.hud.hide()
 var initial_resets: int = app.player.reset_count
 await _settle([10,0,0])
 _record("Authored floor supports visitor",app.player.is_on_floor(),{"position":_array(app.player.position),"colliders":app.collision_info.get("count",0)})
 await _route("Central nave circulation",[10,0,0],[38,0,0])
 await _route("Crossing circulation",[43,0,0],[60,0,0])
 await _route("Nativity exterior circulation",[40,-64,0],[64,-64,0])
 await _route("Nativity left door entry",[50.3,-44,0],[50.3,-25,0])
 await _route("Nativity right door exit",[54.7,-25,0],[54.7,-44,0])
 await _test_column()
 await _test_wall()
 await _test_glory_wall()
 await _test_quick_taps()
 await _settle([18,0,0])
 var entry: Vector3 = app.player.position
 var flight: Dictionary = app.player.set_flight_enabled(true)
 app.player.global_position.y = 80.0
 var landing: Dictionary = app.player.set_flight_enabled(false)
 await _ticks(12)
 _record("Flight returns to ground floor",bool(flight.success) and bool(landing.success) and not app.player.flight_enabled and app.player.is_on_floor() and absf(app.player.position.y-entry.y)<0.08,{"transition":landing})
 app.player.set_flight_enabled(true)
 app.player.global_position = Vector3(450,80,450)
 var fallback: Dictionary = app.player.set_flight_enabled(false)
 await _ticks(12)
 _record("Unsupported flight position returns to last safe floor",bool(fallback.success) and str(fallback.get("return_kind",""))=="last_safe" and app.player.is_on_floor(),{"transition":fallback})
 _record("Jesus tower internal construction volume excluded",app.player._inside_restricted_tower(Vector3(52.5,120,0)) and not app.player._inside_restricted_tower(Vector3(52.5,120,20)),{"exclusion":"radius 9m, elevation 62..175m, conservative approximation"})
 _record("No emergency fall reset",app.player.reset_count==initial_resets,{"resets":app.player.reset_count-initial_resets})
 app._visit(1)
 app._pause()
 var report := {"passed":failures==0,"passed_count":checks.size()-failures,"test_count":checks.size(),"failures":failures,"checks":checks,"elapsed_seconds":(Time.get_ticks_msec()-began)/1000.0,"execution":"browser WebAssembly" if OS.has_feature("web") else "native Godot diagnostic","input_method":"programmatic capsule driving; separate physical input verification required","engine":Engine.get_version_info().string,"renderer":RenderingServer.get_current_rendering_method(),"model":app.model_statistics,"model_source":app.model_source,"colliders":app.collision_info.get("count",0),"as_of_date":"2026-10-01","evidence_date":"2026-09-22"}
 print("SAGRADA_PHYSICS_QA ",JSON.stringify(report))
 progress.emit({"running":false,"passed":report.passed,"failures":failures})
 return report

func _ticks(count: int) -> void:
 for i in count: await get_tree().physics_frame

func _settle(point: Array) -> void:
 app.player.auto_drive = false
 app.player.teleport(point,[],true)
 if app.player.flight_enabled: app.player.set_flight_enabled(false)
 await _ticks(15)

func _route(name: String, start: Array, finish: Array) -> void:
 await _settle(start)
 var target: Vector3 = app.CollisionBuilder.v3(finish)
 var direction: Vector3 = target-app.player.position
 direction.y = 0
 var distance := direction.length()
 app.player.drive_direction = direction.normalized()
 app.player.drive_speed = 8.8
 app.player.auto_drive = true
 await _ticks(int(ceil(distance/8.8*60)))
 app.player.auto_drive = false
 await _ticks(6)
 var error := Vector2(app.player.position.x-target.x,app.player.position.z-target.z).length()
 _record(name,error<0.8 and app.player.is_on_floor(),{"end_error_m":error,"position":_array(app.player.position),"wall_contacts":app.player.wall_contact_count})

func _test_column() -> void:
 var found := false
 for item in app.collider_data.get("colliders",[]):
  if item.get("type","") != "cylinder": continue
  var center: Array = item.get("center",[0,0,0])
  if absf(float(center[1]))>18 or float(center[0])<7 or float(center[0])>44: continue
  var radius := float(item.get("radius",0.6))
  await _settle([float(center[0])-radius-2.2,float(center[1]),0])
  var before: int = app.player.wall_contact_count
  app.player.drive_direction = Vector3.RIGHT
  app.player.drive_speed = 4.4
  app.player.auto_drive = true
  await _ticks(90)
  app.player.auto_drive = false
  var distance := Vector2(app.player.position.x-float(center[0]),app.player.position.z+float(center[1])).length()
  _record("Column collision stops visitor",app.player.wall_contact_count>before and distance>=radius+0.20,{"column":item.get("name",""),"distance_m":distance,"radius_m":radius})
  found = true
  break
 if not found: _record("Column collider available",false,{"reason":"No suitable interior cylinder in source collision data"})

func _test_wall() -> void:
 await _settle([18,-19,0])
 var before: int = app.player.wall_contact_count
 app.player.drive_direction = Vector3(0,0,1)
 app.player.drive_speed = 4.4
 app.player.auto_drive = true
 await _ticks(105)
 app.player.auto_drive = false
 _record("Nave wall blocks walking",app.player.wall_contact_count>before and app.player.position.z<24.0,{"position":_array(app.player.position),"wall_contacts_added":app.player.wall_contact_count-before})

func _array(value: Vector3) -> Array:
 return [value.x,value.y,value.z]

func _test_glory_wall() -> void:
 for item in app.collider_data.get("colliders",[]):
  if item.get("name","") != "Glory_existing_closed_weather_wall_lower": continue
  var center: Array = item.get("center",[0,0,0])
  var size: Array = item.get("size",[1,1,1])
  var exterior_face := float(center[0])-float(size[0])*0.5
  await _settle([exterior_face-4.0,0,0])
  var before: int = app.player.wall_contact_count
  app.player.drive_direction = Vector3.RIGHT
  app.player.drive_speed = 4.4
  app.player.auto_drive = true
  await _ticks(90)
  app.player.auto_drive = false
  _record("Existing closed Glory wall blocks walking",app.player.wall_contact_count>before and app.player.position.x<exterior_face-0.20,{"position":_array(app.player.position),"wall_exterior_x":exterior_face,"wall_contacts_added":app.player.wall_contact_count-before})
  return
 _record("Existing closed Glory wall collider available",false,{"reason":"Expected current-state closed wall collider is missing"})

func _test_quick_taps() -> void:
 await _settle([18,0,0])
 app.player.set_flight_enabled(true)
 app.player.position.y = 4.0
 app.player.active = true
 app.player.drag_look_enabled = true
 for key in [KEY_E,KEY_Q]:
  var before: float = app.player.position.y
  var down := InputEventKey.new()
  down.physical_keycode = key
  down.keycode = key
  down.pressed = true
  Input.parse_input_event(down)
  var up := down.duplicate()
  up.pressed = false
  Input.parse_input_event(up)
  await _ticks(3)
  var difference: float = app.player.position.y-before
  var expected := 0.1 if key==KEY_E else -0.1
  _record("Quick E tap ascends once" if key==KEY_E else "Quick Q tap descends once",absf(difference-expected)<0.012,{"method":"Godot injected keydown and keyup before next physics tick, production input path","delta_m":difference,"expected_m":expected})
 app.player.active = false
 app.player.drag_look_enabled = false
 app.player.set_flight_enabled(false)
