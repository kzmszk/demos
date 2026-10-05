extends RefCounted
## Input uses Blender XYZ. GLTF coordinate conversion is (x,z,-y).

static func v3(values: Array) -> Vector3:
	return Vector3(float(values[0]), float(values[2]), -float(values[1]))

static func build(parent: Node3D, data: Dictionary) -> Dictionary:
	var count := 0
	var names: Array[String] = []
	for item in data.get("colliders", []):
		if not item is Dictionary:
			continue
		var body := StaticBody3D.new()
		body.name = str(item.get("name", "Collider_%d" % count))
		body.set_meta("source_name", str(item.get("name", "")))
		body.set_meta("walkable_floor", bool(item.get("walkable_floor", false)))
		body.collision_layer = 1
		body.collision_mask = 2
		parent.add_child(body)
		body.position = v3(item.get("center", [0, 0, 0]))
		# Blender Z rotation maps to Godot Y; positive direction is preserved.
		body.rotation.y = float(item.get("rotation_z", 0.0))
		var collision := CollisionShape3D.new()
		var kind := str(item.get("type", "box"))
		if kind == "cylinder":
			var shape := CylinderShape3D.new()
			shape.radius = float(item.get("radius", 0.8))
			shape.height = float(item.get("height", 8.0))
			collision.shape = shape
		elif kind == "convex":
			var shape := ConvexPolygonShape3D.new()
			var points := PackedVector3Array()
			for point in item.get("points", []):
				points.append(v3(point))
			shape.points = points
			collision.shape = shape
		else:
			var shape := BoxShape3D.new()
			var size: Array = item.get("size", [1, 1, 1])
			shape.size = Vector3(float(size[0]), float(size[2]), float(size[1]))
			collision.shape = shape
		body.add_child(collision)
		names.append(str(body.name))
		count += 1
	return {"count": count, "names": names}
