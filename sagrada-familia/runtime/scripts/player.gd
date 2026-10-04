extends CharacterBody3D
## Foot-origin capsule controller. Geometry and navigation use metres.
## Walking plus explicit free-camera flight for architectural inspection.
## Flight never changes the last validated walking location.

signal mode_changed(flight_enabled: bool, info: Dictionary)

const EYE_HEIGHT := 1.67
const BODY_HEIGHT := 1.80
const RADIUS := 0.27
const WALK_SPEED := 2.2
const FAST_SPEED := 4.4
const STEP_HEIGHT := 0.30
const GRAVITY := 18.0
const FLIGHT_SPEED := 6.0
const FLIGHT_FAST_SPEED := 18.0
const FLIGHT_MIN_FOOT_HEIGHT := -0.05
const FLIGHT_MAX_FOOT_HEIGHT := 195.0
const FLOOR_MIN_HEIGHT := -0.5
const FLOOR_MAX_HEIGHT := 2.0
const RETURN_FOOT_GAP := 0.014
const ENTRY_SAFE_POSITION := Vector3(52.5, 0.02, 65)

var pending_motion_taps := {}
var frame_motion_taps := {}
const MOTION_ACTIONS := ["move_left","move_right","move_forward","move_back","fly_down","fly_up"]
var restricted_entry_count := 0
var active := false
## Standard drag input for browsers where pointer lock is unavailable. The
## application enables this only after informing the visitor; menus stay gated.
var drag_look_enabled := false
var auto_drive := false
var drive_direction := Vector3.ZERO
var drive_speed := WALK_SPEED
var mouse_sensitivity := 0.0018
var head: Node3D
var camera: Camera3D
var flight_enabled := false
var debug_fly: bool:
	get:
		return flight_enabled
	set(value):
		set_flight_enabled(value)
var last_mode_change: Dictionary = {}
var last_safe_walk_position := ENTRY_SAFE_POSITION
var safe_position_cooldown := 0.0
var body_shape: CapsuleShape3D
var teleport_grace_frames := 2
var step_support_frames := 0
var step_count := 0
var wall_contact_count := 0
var reset_count := 0
var last_safe_position := Vector3(52.5, 0.02, 65)

func _ready() -> void:
	name = "Visitor"
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.36
	floor_max_angle = deg_to_rad(43.0)
	floor_constant_speed = true
	floor_stop_on_slope = true
	max_slides = 6
	safe_margin = 0.002
	var capsule := CapsuleShape3D.new()
	capsule.radius = RADIUS
	capsule.height = BODY_HEIGHT
	body_shape = capsule
	var collision := CollisionShape3D.new()
	collision.shape = capsule
	collision.position.y = BODY_HEIGHT * 0.5
	add_child(collision)
	head = Node3D.new()
	head.name = "EyeLevel"
	head.position.y = EYE_HEIGHT
	add_child(head)
	camera = Camera3D.new()
	camera.name = "Camera"
	camera.current = true
	camera.fov = 68.0
	camera.near = 0.06
	camera.far = 450.0
	head.add_child(camera)

func _unhandled_input(event: InputEvent) -> void:
	# A quick down/up may both arrive between physics ticks. Preserve one tick of
	# intent, merged with held strength, without adding speed or accumulating repeats.
	if event is InputEventKey and event.pressed and not event.echo and _navigation_input_allowed():
		for action in MOTION_ACTIONS:
			if event.is_action_pressed(action): pending_motion_taps[action] = true
	if not active or not event is InputEventMouseMotion:
		return
	# Unhandled events preserve the UI's right to consume pointer input. A visible
	# pointer can roam normally; only a left-button drag rotates the free view.
	var dragging: bool = drag_look_enabled and (int(event.button_mask) & MOUSE_BUTTON_MASK_LEFT) != 0
	if _pointer_is_captured() or dragging:
		apply_look_delta(event.relative)

func _pointer_is_captured() -> bool:
	return Input.mouse_mode == Input.MOUSE_MODE_CAPTURED

func _navigation_input_allowed() -> bool:
	return active and (_pointer_is_captured() or drag_look_enabled)

func apply_look_delta(relative: Vector2) -> void:
	rotate_y(-relative.x * mouse_sensitivity)
	head.rotation.x = clampf(head.rotation.x - relative.y * mouse_sensitivity, deg_to_rad(-85), deg_to_rad(85))

func teleport(blender_pos: Array, target_blender: Array = [], snap_to_ground: bool = false) -> void:
	pending_motion_taps.clear()
	frame_motion_taps.clear()
	global_position = Vector3(float(blender_pos[0]), float(blender_pos[2]) + 0.012, -float(blender_pos[1]))
	if snap_to_ground:
		var query := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 1.0, global_position - Vector3.UP * 2.0, 1, [get_rid()])
		var floor_hit := get_world_3d().direct_space_state.intersect_ray(query)
		if not floor_hit.is_empty() and Vector3(floor_hit.normal).dot(Vector3.UP) > 0.75:
			global_position.y = float(floor_hit.position.y) + 0.012
	velocity = Vector3.ZERO
	camera.position = Vector3.ZERO
	head.position.y = EYE_HEIGHT
	# A waypoint in flight must not become the walking fallback until validated.
	if not flight_enabled:
		last_safe_position = global_position
	step_support_frames = 0
	teleport_grace_frames = 2
	if target_blender.size() == 3:
		var target := Vector3(float(target_blender[0]), float(target_blender[2]), -float(target_blender[1]))
		var direction := (target - camera.global_position).normalized()
		rotation.y = atan2(-direction.x, -direction.z)
		head.rotation.x = asin(clampf(direction.y, -1.0, 1.0))
	if flight_enabled:
		global_position.y = clampf(global_position.y, FLIGHT_MIN_FOOT_HEIGHT, FLIGHT_MAX_FOOT_HEIGHT)
	elif is_inside_tree():
		_remember_safe_walk_position()
	if _inside_restricted_tower(global_position):
		global_position = Vector3(52.5, minf(global_position.y,170.0), -14.0)

func set_flight_enabled(enabled: bool) -> Dictionary:
	if enabled == flight_enabled:
		return {"success": true, "mode": "flight" if enabled else "walk", "return_kind": "unchanged", "message": "", "position": _position_array(global_position)}
	if enabled:
		_remember_safe_walk_position()
		flight_enabled = true
		global_position.y = clampf(global_position.y, FLIGHT_MIN_FOOT_HEIGHT, FLIGHT_MAX_FOOT_HEIGHT)
		velocity = Vector3.ZERO
		step_support_frames = 0
		head.position.y = EYE_HEIGHT
		last_mode_change = {"success": true, "mode": "flight", "return_kind": "none", "message": "飛行モード：E / Spaceで上昇、Q / Cで下降", "position": _position_array(global_position)}
	else:
		var landing := _find_walk_floor(global_position)
		var return_kind := "below"
		if landing.is_empty():
			landing = _find_walk_floor(last_safe_walk_position)
			return_kind = "last_safe"
		if landing.is_empty():
			landing = _find_walk_floor(ENTRY_SAFE_POSITION)
			return_kind = "nativity_parvis"
		if landing.is_empty():
			last_mode_change = {"success": false, "mode": "flight", "return_kind": "unavailable", "message": "安全な床が見つかりません。飛行を続けて入口へ移動してください。", "position": _position_array(global_position)}
			mode_changed.emit(flight_enabled, last_mode_change)
			return last_mode_change
		flight_enabled = false
		global_position = landing.position
		velocity = Vector3.ZERO
		camera.position = Vector3.ZERO
		head.position.y = EYE_HEIGHT
		step_support_frames = 0
		teleport_grace_frames = 2
		last_safe_walk_position = global_position
		last_safe_position = global_position
		last_mode_change = {"success": true, "mode": "walk", "return_kind": return_kind, "message": "歩行モード：直下の床へ戻りました" if return_kind == "below" else "歩行モード：安全な歩行位置へ戻りました", "position": _position_array(global_position)}
	mode_changed.emit(flight_enabled, last_mode_change)
	return last_mode_change

func toggle_flight() -> Dictionary:
	return set_flight_enabled(not flight_enabled)

func _position_array(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func _is_walk_floor(body: Object) -> bool:
	if not is_instance_valid(body):
		return false
	if body.has_meta("walkable_floor"):
		return bool(body.get_meta("walkable_floor"))
	var source_name := str(body.get_meta("source_name", body.name)).to_lower().replace(" ", "_")
	# Allow only authored low floors/steps. Furniture, roofs, walls and pier tops
	# must never become walking return surfaces, even when their tops are low.
	return source_name in ["parvis", "nave_floor", "ambulatory_floor", "axial_floor"] or source_name.begins_with("sanctuary_step_") or source_name.begins_with("crossing_altar_step") or source_name.begins_with("fixture_floor")

func _floor_probe(location: Vector3) -> Dictionary:
	var start := Vector3(location.x, FLOOR_MAX_HEIGHT + 0.4, location.z)
	var end := Vector3(location.x, FLOOR_MIN_HEIGHT - 0.2, location.z)
	var query := PhysicsRayQueryParameters3D.create(start, end, 1, [get_rid()])
	query.hit_from_inside = true
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or not _is_walk_floor(hit.collider):
		return {}
	if hit.position.y < FLOOR_MIN_HEIGHT or hit.position.y > FLOOR_MAX_HEIGHT or Vector3(hit.normal).dot(Vector3.UP) < cos(floor_max_angle):
		return {}
	return hit

func _find_walk_floor(location: Vector3) -> Dictionary:
	if not is_inside_tree() or body_shape == null:
		return {}
	var center_hit := _floor_probe(location)
	if center_hit.is_empty():
		return {}
	var candidate: Vector3 = center_hit.position + Vector3.UP * RETURN_FOOT_GAP
	# Require support under the capsule footprint, not just one ray at a ledge.
	for offset in [Vector3(RADIUS * 0.75, 0, 0), Vector3(-RADIUS * 0.75, 0, 0), Vector3(0, 0, RADIUS * 0.75), Vector3(0, 0, -RADIUS * 0.75)]:
		var support := _floor_probe(candidate + offset)
		if support.is_empty() or absf(float(support.position.y) - float(center_hit.position.y)) > STEP_HEIGHT:
			return {}
	var shape_query := PhysicsShapeQueryParameters3D.new()
	shape_query.shape = body_shape
	shape_query.transform = Transform3D(Basis.IDENTITY, candidate + Vector3.UP * BODY_HEIGHT * 0.5)
	shape_query.collision_mask = 1
	shape_query.exclude = [get_rid()]
	shape_query.margin = 0.002
	if not get_world_3d().direct_space_state.intersect_shape(shape_query, 1).is_empty():
		return {}
	return {"position": candidate, "collider": center_hit.collider}

func _remember_safe_walk_position() -> void:
	if flight_enabled:
		return
	var supported := _find_walk_floor(global_position)
	if not supported.is_empty() and absf(float(supported.position.y) - global_position.y) < 0.12:
		last_safe_walk_position = supported.position

func _process_flight(delta: float) -> void:
	velocity = Vector3.ZERO
	if not _navigation_input_allowed():
		return
	var axis := _motion_axis()
	var elevation := _motion_strength("fly_up") - _motion_strength("fly_down")
	var wish := camera.global_basis * Vector3(axis.x, 0.0, axis.y) + Vector3.UP * elevation
	if wish.length_squared() > 1.0:
		wish = wish.normalized()
	var speed := FLIGHT_FAST_SPEED if Input.is_action_pressed("move_fast") else FLIGHT_SPEED
	# Deliberately no collision in inspection flight; walking is restored only
	# after the low-floor and capsule-clearance validation above.
	var proposed := global_position + wish * delta * speed
	if not _inside_restricted_tower(proposed):
		global_position = proposed
	else:
		restricted_entry_count += 1
	global_position.y = clampf(global_position.y, FLIGHT_MIN_FOOT_HEIGHT, FLIGHT_MAX_FOOT_HEIGHT)

func _physics_process(delta: float) -> void:
	frame_motion_taps = pending_motion_taps
	pending_motion_taps = {}
	head.position.y = move_toward(head.position.y, EYE_HEIGHT, delta * 2.8)
	if flight_enabled:
		_process_flight(delta)
		return
	var wish := Vector3.ZERO
	var speed := WALK_SPEED
	if auto_drive:
		wish = drive_direction
		speed = drive_speed
	elif _navigation_input_allowed():
		var axis := _motion_axis()
		wish = global_basis * Vector3(axis.x, 0.0, axis.y)
		speed = FAST_SPEED if Input.is_action_pressed("move_fast") else WALK_SPEED
	wish.y = 0.0
	if wish.length_squared() > 1.0:
		wish = wish.normalized()
	velocity.x = wish.x * speed
	velocity.z = wish.z * speed
	if not is_on_floor() or teleport_grace_frames > 0:
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = -0.2
	if (teleport_grace_frames == 0 and (is_on_floor() or step_support_frames > 0) and velocity.y <= 0.0) and wish.length_squared() > 0.01:
		_try_step(Vector3(velocity.x, 0.0, velocity.z) * delta)
	move_and_slide()
	step_support_frames = maxi(0, step_support_frames - 1)
	teleport_grace_frames = maxi(0, teleport_grace_frames - 1)
	if is_on_wall():
		wall_contact_count += 1
	if is_on_floor() and global_position.y > -2.0:
		last_safe_position = global_position
		safe_position_cooldown -= delta
		if safe_position_cooldown <= 0.0:
			_remember_safe_walk_position()
			safe_position_cooldown = 0.25
	if global_position.y < -12.0:
		global_position = last_safe_position + Vector3.UP * 0.1
		velocity = Vector3.ZERO
		reset_count += 1

func _try_step(travel: Vector3) -> bool:
	# The full capsule must clear up/forward/down. A separate tread ray verifies
	# the actual surface normal, since a capsule touching a sharp tread edge
	# reports the sphere-edge contact normal rather than the flat tread normal.
	if not test_move(global_transform, travel):
		return false
	var direction := travel.normalized()
	var tread_probe := global_position + direction * (RADIUS + travel.length() + 0.035)
	var query := PhysicsRayQueryParameters3D.create(tread_probe + Vector3.UP * (STEP_HEIGHT + 0.025), tread_probe - Vector3.UP * 0.025, 1, [get_rid()])
	var tread := get_world_3d().direct_space_state.intersect_ray(query)
	if tread.is_empty() or Vector3(tread.normal).dot(Vector3.UP) < cos(floor_max_angle):
		return false
	var tread_rise: float = tread.position.y - global_position.y
	if tread_rise <= 0.012 or tread_rise > STEP_HEIGHT + 0.002:
		return false
	var lift := tread_rise + 0.006
	var raised := global_transform
	if test_move(raised, Vector3.UP * lift):
		return false
	raised.origin.y += lift
	if test_move(raised, travel):
		return false
	raised.origin += travel
	var landing := KinematicCollision3D.new()
	if not test_move(raised, Vector3.DOWN * (lift + 0.04), landing):
		return false
	if landing.get_collider() != tread.collider:
		return false
	var rise := lift + landing.get_travel().y
	if rise <= 0.003 or rise > STEP_HEIGHT + 0.001:
		return false
	global_position.y += rise
	head.position.y -= rise
	velocity.y = 0.0
	step_support_frames = 3
	step_count += 1
	return true

func _inside_restricted_tower(point: Vector3) -> bool:
	# Current Jesus tower exterior is complete; interior remains a construction zone.
	# Conservative authored exclusion, not a claim about surveyed internal geometry.
	return point.y > 62.0 and point.y < 175.0 and Vector2(point.x - 52.5, point.z).length() < 9.0

func _motion_strength(action: String) -> float:
	return maxf(Input.get_action_strength(action), 1.0 if frame_motion_taps.has(action) else 0.0)

func _motion_axis() -> Vector2:
	return Vector2(_motion_strength("move_right") - _motion_strength("move_left"), _motion_strength("move_back") - _motion_strength("move_forward")).limit_length(1.0)
