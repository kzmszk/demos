extends Node3D

const PlayerScript = preload("res://scripts/player.gd")
const CollisionBuilder = preload("res://scripts/collision_builder.gd")
const ExteriorGlassShader = preload("res://scripts/exterior_glass.gdshader")
const LIGHTING_PROFILES := {
 "v10":{"ambient_energy":0.44,"neutral_fill_multiplier":1.0,"sun_yaw_degrees":-148.0,"ssao_radius":1.6,"ssao_intensity":1.4,"sun_shadow_normal_bias":0.6,"neutral_shadows":false,"neutral_shadow_opacity":1.0},
 "stone_a":{"ambient_energy":0.30,"neutral_fill_multiplier":0.45,"sun_yaw_degrees":-148.0,"ssao_radius":1.6,"ssao_intensity":1.4,"sun_shadow_normal_bias":0.6,"neutral_shadows":false,"neutral_shadow_opacity":1.0},
 "stone_b":{"ambient_energy":0.30,"neutral_fill_multiplier":0.45,"sun_yaw_degrees":-32.0,"ssao_radius":1.6,"ssao_intensity":1.4,"sun_shadow_normal_bias":0.6,"neutral_shadows":false,"neutral_shadow_opacity":1.0},
 "stone_c":{"ambient_energy":0.12,"neutral_fill_multiplier":0.25,"sun_yaw_degrees":-32.0,"ssao_radius":0.85,"ssao_intensity":2.1,"sun_shadow_normal_bias":0.35,"neutral_shadows":false,"neutral_shadow_opacity":1.0},
 "stone_d":{"ambient_energy":0.12,"neutral_fill_multiplier":0.45,"sun_yaw_degrees":-32.0,"ssao_radius":0.85,"ssao_intensity":2.1,"sun_shadow_normal_bias":0.35,"neutral_shadows":true,"neutral_shadow_opacity":1.0},
 "stone_e":{"ambient_energy":0.12,"neutral_fill_multiplier":0.45,"sun_yaw_degrees":-32.0,"ssao_radius":0.85,"ssao_intensity":2.1,"sun_shadow_normal_bias":0.35,"neutral_shadows":true,"neutral_shadow_opacity":0.65,"neutral_energy_multipliers":{"Vault fill 53":1.15,"Vault fill 72":1.15}}
}
const WAYPOINTS := [
 {"name":"生誕のファサード", "pos":[52.5,-70,0], "look":[52.5,-24,45]},
 {"name":"身廊 · 樹木状の柱", "pos":[10,0,0], "look":[60,0,29]},
 {"name":"交差部 · 60mのヴォールト", "pos":[52.5,-3.8,0], "look":[56,0,57]},
 {"name":"受難のファサード", "pos":[52.5,76,0], "look":[52.5,24,48]},
 {"name":"後陣 · 祭壇を望む", "pos":[67,-12,0], "look":[78,0,17]},
 {"name":"栄光のファサード · 工事中", "pos":[-30,0,0], "look":[8,0,38]},
 {"name":"赤橙のステンドグラス", "pos":[20,11.5,0], "look":[18.75,22.5,13]},
 {"name":"青緑のステンドグラス", "pos":[20,-11.5,0], "look":[18.75,-22.5,13]},
 {"name":"生誕の植物の扉", "pos":[52.5,-46,0], "look":[52.5,-35,6]}
]
var player
var environment: Environment
var sun: DirectionalLight3D
var environment_root: Node3D
var menu: Control
var hud: Control
var place_label: Label
var mode_label: Label
var status_label: Label
var flight_button: Button
var quality := 2
var ready_to_visit := false
var started := false
var photo_mode := false
var frame_times: Array[float] = []
var frame_last_usec := 0
var state_elapsed := 0.0
var uptime := 0.0
var place := "生誕のファサード"
var collision_info := {}
var web_lights: Array[SpotLight3D] = []
var neutral_shadow_lights: Array[OmniLight3D] = []
var active_neutral_shadows: Array[String] = []
var js_callback
var pointer_was_captured := false
var last_mode_info := {}
var model_statistics := {"meshes":0,"triangles":0,"side_aware_glass_surfaces":0}
var glass_material_pairs := {}
var qa_drive_seconds := 0.0
var qa_drive_command := ""
var pointer_capture_pending := 0.0
var input_notice := ""
var quality_button: OptionButton
var qa_before := {}
var qa_result := {}
var qa_busy := false
var qa_progress := {}
var qa_suite_report := {}
var loading_label: Label
var model_source := {}
var collider_data := {}
var command_args := OS.get_cmdline_user_args()
var lighting_profile := "stone_e"

func _ready() -> void:
 Engine.max_fps = 60
 for argument in command_args:
  if argument.begins_with("--resolution=") and DisplayServer.get_name() != "headless":
   var dimensions := argument.get_slice("=",1).split("x")
   if dimensions.size()==2: get_window().size = Vector2i(maxi(800,int(dimensions[0])),maxi(450,int(dimensions[1])))
 _register_inputs()
 var settings := ConfigFile.new()
 if settings.load("user://web_settings.cfg") == OK:
  quality = clampi(int(settings.get_value("display","quality",1)),0,2)
 _resolve_lighting_profile()
 _setup_environment()
 player = PlayerScript.new()
 add_child(player)
 player.mode_changed.connect(_mode_changed)
 player.teleport(WAYPOINTS[0].pos, WAYPOINTS[0].look)
 _build_ui()
 await get_tree().process_frame
 var loaded := _load_geometry()
 var collision_root := Node3D.new()
 add_child(collision_root)
 var collision_path := _asset_path("colliders.json")
 if FileAccess.file_exists(collision_path):
  var data = JSON.parse_string(FileAccess.get_file_as_string(collision_path))
  if data is Dictionary:
   collider_data = data
   collision_info = CollisionBuilder.build(collision_root, data)
 _apply_quality(quality)
 ready_to_visit = loaded and int(collision_info.get("count",0)) > 0
 loading_label.text = "公式資料確認: 2026年9月22日 · 2026年10月1日版" if ready_to_visit else "モデルまたは歩行用データが未作成です。docs/RUNTIME.md を参照してください。"
 if not ready_to_visit:
  push_error("Sagrada geometry or collision data unavailable")
  if "--qa" in command_args: get_tree().quit(2)
  return
 if OS.has_feature("web"):
  js_callback = JavaScriptBridge.create_callback(_web_command)
  var window = JavaScriptBridge.get_interface("window")
  window.sfCommand = js_callback
  JavaScriptBridge.eval("window.sfReady && window.sfReady()")
 print("SAGRADA_READY: ", model_statistics, " collisions: ", collision_info.count," lighting: ",lighting_profile," ",LIGHTING_PROFILES[lighting_profile])
 if "--qa" in command_args:
  await _run_native_qa()
 elif "--capture" in command_args:
  await _capture_native_views()
 elif "--benchmark" in command_args:
  await _benchmark_native_views()
 elif "--start" in command_args:
  _begin(1)

func _register_inputs() -> void:
 var bindings := {"move_forward":[KEY_W,KEY_UP],"move_back":[KEY_S,KEY_DOWN],"move_left":[KEY_A,KEY_LEFT],"move_right":[KEY_D,KEY_RIGHT],"move_fast":[KEY_SHIFT],"fly_up":[KEY_E,KEY_SPACE],"fly_down":[KEY_Q,KEY_C]}
 for action in bindings:
  if not InputMap.has_action(action): InputMap.add_action(action)
  for key in bindings[action]:
   var event := InputEventKey.new()
   event.physical_keycode = key
   InputMap.action_add_event(action,event)

func _asset_path(filename: String) -> String:
 if OS.has_feature("web"): return "res://assets/" + filename
 return ProjectSettings.globalize_path("res://../build/" + filename)

func _resolve_lighting_profile() -> void:
 var requested := "stone_e"
 for argument in command_args:
  if argument.begins_with("--lighting-profile="):
   requested = argument.trim_prefix("--lighting-profile=")
 if OS.has_feature("web"):
  var query = JavaScriptBridge.eval("new URLSearchParams(window.location.search).get('lighting') || ''")
  if query != null and str(query) != "": requested = str(query)
 if LIGHTING_PROFILES.has(requested):
  lighting_profile = requested
 else:
  push_warning("Unknown lighting profile; retaining stone_e: "+requested)

func _load_geometry() -> bool:
 var path := _asset_path("sagrada_familia.glb")
 if not OS.has_feature("web"):
  for argument in command_args:
   if argument.begins_with("--model="): path = argument.trim_prefix("--model=")
 if OS.has_feature("web"):
  if not ResourceLoader.exists(path): return false
 elif not FileAccess.file_exists(path): return false
 var model: Node3D
 if OS.has_feature("web"):
  var packed = load(path)
  if not packed is PackedScene: return false
  model = packed.instantiate()
 else:
  var document := GLTFDocument.new()
  var state := GLTFState.new()
  if document.append_from_file(path,state) != OK: return false
  for material in state.get_materials():
   if not material is BaseMaterial3D: continue
   for slot in [BaseMaterial3D.TEXTURE_ALBEDO,BaseMaterial3D.TEXTURE_NORMAL,BaseMaterial3D.TEXTURE_ROUGHNESS,BaseMaterial3D.TEXTURE_EMISSION]:
    var texture = material.get_texture(slot)
    if texture == null: continue
    var image: Image = texture.get_image()
    if image == null: continue
    if image.is_compressed(): image.decompress()
    if not image.has_mipmaps(): image.generate_mipmaps(slot == BaseMaterial3D.TEXTURE_NORMAL)
    material.set_texture(slot,ImageTexture.create_from_image(image))
  model = document.generate_scene(state)
 if model == null: return false
 add_child(model)
 model.name = "SagradaFamilia_CurrentEvidence"
 _prepare_model(model)
 player.camera.make_current()
 if OS.has_feature("web"):
  var manifest_path := "res://assets/source_manifest.json"
  if FileAccess.file_exists(manifest_path):
   var manifest = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
   if manifest is Dictionary: model_source = manifest.get("sagrada_familia.glb",{})
 else:
  model_source = {"path":path,"sha256":FileAccess.get_sha256(path),"bytes":FileAccess.open(path,FileAccess.READ).get_length()}
 return true

func _setup_environment() -> void:
 environment_root = Node3D.new()
 environment_root.name = "DaylightApproximation"
 add_child(environment_root)
 var world := WorldEnvironment.new()
 environment = Environment.new()
 world.environment = environment
 add_child(world)
 environment.background_mode = Environment.BG_SKY
 var sky := Sky.new()
 var skymat := ProceduralSkyMaterial.new()
 skymat.sky_top_color = Color(0.22,0.40,0.61)
 skymat.sky_horizon_color = Color(0.72,0.78,0.81)
 skymat.ground_bottom_color = Color(0.29,0.27,0.23)
 skymat.ground_horizon_color = Color(0.68,0.70,0.71)
 skymat.sky_curve = 0.22
 sky.sky_material = skymat
 environment.sky = sky
 environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
 environment.ambient_light_color = Color(0.91,0.92,0.96)
 environment.ambient_light_energy = float(LIGHTING_PROFILES[lighting_profile].ambient_energy)
 environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
 environment.tonemap_mode = Environment.TONE_MAPPER_AGX
 environment.tonemap_exposure = 1.25
 environment.tonemap_agx_contrast = 1.05
 # Compatibility consumes radius/intensity; smaller radius concentrates the C
 # comparison near contacts rather than darkening broad stone surfaces.
 environment.ssao_radius = float(LIGHTING_PROFILES[lighting_profile].ssao_radius)
 environment.ssao_intensity = float(LIGHTING_PROFILES[lighting_profile].ssao_intensity)
 environment.ssao_power = 1.1
 environment.ssao_light_affect = 0.25
 environment.glow_intensity = 0.16
 environment.glow_bloom = 0.01
 sun = DirectionalLight3D.new()
 sun.name = "MediterraneanDaylight"
 sun.rotation_degrees = Vector3(-46,float(LIGHTING_PROFILES[lighting_profile].sun_yaw_degrees),0)
 sun.light_color = Color(1.0,0.94,0.83)
 sun.light_energy = 1.7
 sun.shadow_enabled = true
 sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
 sun.directional_shadow_max_distance = 200.0
 sun.directional_shadow_pancake_size = 0.0
 sun.directional_shadow_split_1 = 0.05
 sun.directional_shadow_split_2 = 0.16
 sun.directional_shadow_split_3 = 0.42
 sun.directional_shadow_blend_splits = true
 sun.shadow_bias = 0.04
 # C reduces normal-offset separation at contacts; constant bias stays 0.04.
 # Real Web review must check for acne as well as restored contact shadows.
 sun.shadow_normal_bias = float(LIGHTING_PROFILES[lighting_profile].sun_shadow_normal_bias)
 environment_root.add_child(sun)
 # Authored real-time light approximation, never presented as measured daylight.
 var path := _asset_path("runtime_lighting.json")
 if not FileAccess.file_exists(path): return
 var spec = JSON.parse_string(FileAccess.get_file_as_string(path))
 if not spec is Dictionary: return
 for item in spec.get("spot_lights",[]):
  _window_light(item)
 for item in spec.get("point_lights",[]):
  var lamp := OmniLight3D.new()
  lamp.name = str(item.get("name","StoneBounce"))
  lamp.position = CollisionBuilder.v3(item.get("position",[35,0,14]))
  var color: Array = item.get("color",[1,1,1])
  lamp.light_color = Color(float(color[0]),float(color[1]),float(color[2]))
  lamp.light_energy = float(item.get("energy",0.25))
  # A/B lighting review: only the five neutral vault fills are attenuated.
  # The photographed glazing and all Glass spill colour/energy stay unchanged.
  if lamp.name.begins_with("Vault fill "):
   lamp.light_energy *= float(LIGHTING_PROFILES[lighting_profile].neutral_fill_multiplier)
   # Restore a little light in the rear nave/apse after closing the roof seams.
   # Named E-only gains preserve every other neutral and coloured-glass lamp.
   var local_gains: Dictionary = LIGHTING_PROFILES[lighting_profile].get("neutral_energy_multipliers",{})
   lamp.light_energy *= float(local_gains.get(str(lamp.name),1.0))
   # Compatibility supports opacity mixing for Omni shadows; this reduces
   # contrast as a bounce-light approximation, without claiming softer edges.
   lamp.shadow_opacity = float(LIGHTING_PROFILES[lighting_profile].neutral_shadow_opacity)
   if bool(LIGHTING_PROFILES[lighting_profile].neutral_shadows):
    neutral_shadow_lights.append(lamp)
  lamp.omni_range = float(item.get("range",15))
  lamp.omni_attenuation = float(item.get("attenuation",1.5))
  lamp.shadow_enabled = false
  environment_root.add_child(lamp)

func _window_light(item: Dictionary) -> void:
 var lamp := SpotLight3D.new()
 lamp.name = str(item.get("name","WindowColour"))
 environment_root.add_child(lamp)
 lamp.position = CollisionBuilder.v3(item.get("position",[30,-21,15]))
 lamp.look_at(CollisionBuilder.v3(item.get("target",[32,0,0])),Vector3.UP)
 lamp.light_energy = float(item.get("energy",1.0))
 var color: Array = item.get("color",[1,1,1])
 lamp.light_color = Color(float(color[0]),float(color[1]),float(color[2]))
 lamp.spot_range = float(item.get("range",38))
 lamp.spot_angle = float(item.get("angle",48))
 lamp.spot_attenuation = 0.85
 lamp.shadow_enabled = false
 lamp.shadow_bias = 0.06
 lamp.shadow_normal_bias = 0.4
 lamp.distance_fade_enabled = true
 lamp.distance_fade_begin = 55.0
 lamp.distance_fade_length = 20.0
 web_lights.append(lamp)

func _prepare_model(node: Node) -> void:
 if node is Camera3D: node.current = false
 if node is MeshInstance3D and node.mesh:
  if str(node.name).to_lower().contains("ground") or str(node.name).to_lower().contains("floor"):
   node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
  model_statistics.meshes += 1
  for i in node.mesh.get_surface_count():
   model_statistics.triangles += node.mesh.surface_get_array_index_len(i)/3
   var mat = node.mesh.surface_get_material(i)
   if mat is BaseMaterial3D:
    mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
    var glass_name := str(mat.resource_name)
    if not "--baseline-glass" in command_args and (glass_name.contains("photographed bank") or (glass_name.begins_with("Original abstract ") and glass_name.contains("glazing"))):
     node.set_surface_override_material(i,_side_aware_glass(mat))
     model_statistics.side_aware_glass_surfaces += 1
 for child in node.get_children(): _prepare_model(child)

func _side_aware_glass(source: BaseMaterial3D) -> BaseMaterial3D:
 var identity := source.get_instance_id()
 if glass_material_pairs.has(identity): return glass_material_pairs[identity]
 var interior := source.duplicate() as BaseMaterial3D
 interior.cull_mode = BaseMaterial3D.CULL_FRONT
 var outside := ShaderMaterial.new()
 outside.shader = ExteriorGlassShader
 outside.resource_name = source.resource_name + " · non-emissive exterior"
 outside.set_shader_parameter("original_albedo",source.albedo_color)
 var texture := source.get_texture(BaseMaterial3D.TEXTURE_ALBEDO)
 outside.set_shader_parameter("use_texture",texture != null)
 if texture != null: outside.set_shader_parameter("original_texture",texture)
 outside.set_shader_parameter("use_vertex_color",source.vertex_color_use_as_albedo)
 outside.set_shader_parameter("vertex_color_is_srgb",source.vertex_color_is_srgb)
 outside.set_shader_parameter("uv_scale",source.uv1_scale)
 outside.set_shader_parameter("uv_offset",source.uv1_offset)
 interior.next_pass = outside
 glass_material_pairs[identity] = interior
 return interior

func _build_ui() -> void:
 var layer := CanvasLayer.new()
 add_child(layer)
 var theme := Theme.new()
 theme.default_font_size = 18
 if ResourceLoader.exists("res://assets/sagrada_familia_ui.woff2"):
  theme.default_font = load("res://assets/sagrada_familia_ui.woff2")
 menu = Control.new()
 menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 menu.theme = theme
 layer.add_child(menu)
 var shade := ColorRect.new()
 shade.color = Color(0.017,0.022,0.031,0.86)
 shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 menu.add_child(shade)
 var center := CenterContainer.new()
 center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 menu.add_child(center)
 var card := VBoxContainer.new()
 card.custom_minimum_size = Vector2(750,0)
 card.add_theme_constant_override("separation",16)
 center.add_child(card)
 card.add_child(_label("BARCELONA  /  CONSTRUCTION STUDY 2026",14,Color(0.82,0.69,0.43)))
 card.add_child(_label("SAGRADA FAMÍLIA",58,Color(0.97,0.94,0.87)))
 card.add_child(_label("光の森を歩く。いまの姿を、空から見る。",23,Color(0.8,0.82,0.83)))
 card.add_child(HSeparator.new())
 var buttons := HBoxContainer.new()
 buttons.add_theme_constant_override("separation",12)
 card.add_child(buttons)
 _button(buttons,"身廊から歩く",func(): _begin(1))
 _button(buttons,"生誕のファサードへ",func(): _begin(0))
 _button(buttons,"再開",func(): _resume())
 var places := OptionButton.new()
 places.custom_minimum_size.y = 44
 for waypoint in WAYPOINTS: places.add_item(str(waypoint.name))
 places.item_selected.connect(func(index): _begin(index))
 card.add_child(places)
 flight_button = _button(card,"飛行モードに切替  /  F",func(): _toggle_flight())
 card.add_child(_label("WASD  移動  ·  Mouse  視線  ·  Shift  高速\nF  歩行 / 飛行  ·  E / Space  上昇  ·  Q / C  下降\n1–9  見学地点  ·  Esc  ポインタ解除 / メニュー\nP  表示を隠す  ·  F3  FPS",16,Color(0.73,0.77,0.80)))
 card.add_child(_label("イエス塔は外装完成・内部工事中。内部への飛行は制限されます。\n栄光のファサードと被昇天礼拝堂は未完成の姿で表現します。",14,Color(0.65,0.7,0.73)))
 var options := HBoxContainer.new()
 card.add_child(options)
 options.add_child(_label("画質  ",16,Color(0.8,0.8,0.78)))
 var q := OptionButton.new()
 quality_button = q
 for label in ["Low · 軽量","Medium · 標準","High · 高品質"]:q.add_item(label)
 q.select(quality)
 q.item_selected.connect(_apply_quality)
 options.add_child(q)
 loading_label = _label("資料と建築データを準備しています…",12,Color(0.65,0.7,0.73))
 card.add_child(loading_label)
 card.add_child(_label("現状資料に基づく再構成。細部に推定・簡略化を含み、照明は鑑賞用の近似です。",12,Color(0.55,0.6,0.64)))
 hud = Control.new()
 hud.theme = theme
 hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
 layer.add_child(hud)
 place_label = _label("SAGRADA FAMÍLIA",15,Color(0.98,0.96,0.88,0.9))
 place_label.position = Vector2(28,24)
 hud.add_child(place_label)
 mode_label = _label("WALK  ·  F: FLY  ·  ESC: MENU",14,Color(0.88,0.90,0.92,0.9))
 mode_label.position = Vector2(28,48)
 hud.add_child(mode_label)
 status_label = _label("",12,Color(0.85,0.87,0.92))
 status_label.position = Vector2(28,72)
 status_label.visible = false
 hud.add_child(status_label)
 hud.hide()
 if OS.has_feature("web"):menu.modulate.a = 0.0

func _label(text: String,size: int,color: Color) -> Label:
 var node := Label.new()
 node.text = text
 node.add_theme_font_size_override("font_size",size)
 node.add_theme_color_override("font_color",color)
 node.add_theme_color_override("font_shadow_color",Color(0,0,0,0.8))
 node.add_theme_constant_override("shadow_offset_x",1)
 node.add_theme_constant_override("shadow_offset_y",1)
 return node

func _button(parent: Node,text: String,action: Callable) -> Button:
 var button := Button.new()
 button.text = text
 button.focus_mode = Control.FOCUS_NONE
 button.custom_minimum_size.y = 46
 button.pressed.connect(action)
 parent.add_child(button)
 return button

func _begin(index: int) -> void:
 if not ready_to_visit: return
 _visit(index)
 started = true
 _resume()

func _visit(index: int) -> void:
 player.teleport(WAYPOINTS[index].pos,WAYPOINTS[index].look,true)
 if player.flight_enabled:
  var result: Dictionary = player.set_flight_enabled(false)
  if not result.success:
   _pause()
   return
 place = WAYPOINTS[index].name
 place_label.text = "SAGRADA FAMÍLIA  /  " + place.to_upper()

func _resume() -> void:
 if not ready_to_visit:return
 if not started:
  _begin(1)
  return
 menu.hide()
 hud.visible = not OS.has_feature("web") and not photo_mode
 player.active = true
 player.drag_look_enabled = false
 Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
 pointer_was_captured = false
 pointer_capture_pending = 2.0

func _pause() -> void:
 player.active = false
 player.pending_motion_taps.clear()
 player.frame_motion_taps.clear()
 pointer_capture_pending = 0.0
 menu.show()
 hud.hide()
 Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
 pointer_was_captured = false

func _toggle_flight() -> void:
 if not ready_to_visit: return
 if not started:
  _visit(1)
  started = true
 player.toggle_flight()
 if menu.visible:_resume()

func _mode_changed(flying: bool, info: Dictionary) -> void:
 last_mode_info = info
 if mode_label:
  mode_label.text = "FLY  ·  E / SPACE: UP  ·  Q / C: DOWN  ·  F: WALK" if flying else "WALK  ·  F: FLY  ·  ESC: MENU"
 if flight_button:flight_button.text = "歩行に戻る  /  F" if flying else "飛行モードに切替  /  F"

func _unhandled_input(event: InputEvent) -> void:
 if qa_busy:return
 if not event is InputEventKey or not event.pressed or event.echo:return
 match event.physical_keycode:
  KEY_ESCAPE: _pause()
  KEY_F: _toggle_flight()
  KEY_F1: _pause()
  KEY_F3: status_label.visible = not status_label.visible
  KEY_P:
   photo_mode = not photo_mode
   hud.visible = not OS.has_feature("web") and not photo_mode and not menu.visible
  _:
   if event.physical_keycode>=KEY_1 and event.physical_keycode<=KEY_9 and started:
    _visit(event.physical_keycode-KEY_1)

func _apply_quality(index: int) -> void:
 quality = clampi(index,0,2)
 if quality_button:quality_button.select(quality)
 get_viewport().msaa_3d = [Viewport.MSAA_DISABLED,Viewport.MSAA_2X,Viewport.MSAA_4X][quality]
 get_viewport().use_taa = false
 get_viewport().scaling_3d_scale = [0.70,0.90,1.0][quality]
 environment.ssao_enabled = quality>=1
 environment.glow_enabled = quality==2
 RenderingServer.directional_shadow_atlas_set_size([2048,4096,4096][quality],true)
 get_viewport().positional_shadow_atlas_size = [1024,2048,4096][quality]
 _update_local_shadows()
 var settings := ConfigFile.new()
 settings.set_value("display","quality",quality)
 settings.save("user://web_settings.cfg")

func _update_local_shadows() -> void:
 # Legacy spot budgets stay unchanged. D adds only nearby neutral Omni shadows;
 # the photographed-glass spill lamps never enter this list or change energy.
 var nearby := web_lights.duplicate()
 nearby.sort_custom(func(a,b):return a.position.distance_squared_to(player.camera.global_position)<b.position.distance_squared_to(player.camera.global_position))
 for light in web_lights:light.shadow_enabled = false
 for i in mini([0,2,4][quality],nearby.size()):nearby[i].shadow_enabled=true
 var neutral_nearby := neutral_shadow_lights.duplicate()
 neutral_nearby.sort_custom(func(a,b):return a.position.distance_squared_to(player.camera.global_position)<b.position.distance_squared_to(player.camera.global_position))
 active_neutral_shadows.clear()
 for light in neutral_shadow_lights:light.shadow_enabled = false
 for i in mini([0,1,2][quality],neutral_nearby.size()):
  neutral_nearby[i].shadow_enabled = true
  active_neutral_shadows.append(str(neutral_nearby[i].name))

func _process(delta: float) -> void:
 uptime += delta
 if pointer_capture_pending > 0.0:
  pointer_capture_pending -= delta
  if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
   pointer_was_captured = true
   pointer_capture_pending = 0.0
  elif pointer_capture_pending <= 0.0:
   _enable_drag_look()
 if started and pointer_was_captured and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:_pause()
 if not ready_to_visit:return
 var wall_now := Time.get_ticks_usec()
 if frame_last_usec > 0: frame_times.append(float(wall_now-frame_last_usec)/1000.0)
 frame_last_usec = wall_now
 if frame_times.size()>600:frame_times.pop_front()
 if qa_drive_seconds>0:
  qa_drive_seconds -= delta
  if qa_drive_seconds<=0:
   Input.action_release(qa_drive_command)
   qa_result = {"test":qa_before.get("test",""),"before":qa_before,"after":_visitor_snapshot()}
   qa_drive_command = ""
 state_elapsed += delta
 if state_elapsed<0.5:return
 state_elapsed = 0
 var p: Vector3 = player.global_position
 status_label.text = "%d FPS · 高度 %.1f m" % [Engine.get_frames_per_second(),p.y+1.67]
 _update_local_shadows()
 if OS.has_feature("web"):
  var mean := 0.0
  for value in frame_times:mean += value
  mean /= maxi(1,frame_times.size())
  var report := {"ready":ready_to_visit,"mode":"fly" if player.flight_enabled else "walk","active":player.active,"pointer":Input.mouse_mode==Input.MOUSE_MODE_CAPTURED,"menu":menu.visible,"photo_mode":photo_mode,"position":[snappedf(p.x,.001),snappedf(p.y,.001),snappedf(p.z,.001)],"eye_height":snappedf(player.camera.global_position.y,.001),"fps":Engine.get_frames_per_second(),"mean_fps":1000.0/maxf(.1,mean),"quality":quality,"lighting_profile":lighting_profile,"lighting_profile_settings":LIGHTING_PROFILES[lighting_profile],"active_neutral_shadows":active_neutral_shadows,"place":place,"resets":player.reset_count,"on_floor":player.is_on_floor() and not player.flight_enabled,"last_transition":last_mode_info,"uptime":snappedf(uptime,.01),"wall_uptime_seconds":Time.get_ticks_msec()/1000.0,"fps_method":"monotonic wall-clock frame intervals","qa_result":qa_result,"qa_busy":qa_busy,"qa_progress":qa_progress,"qa_suite_report":qa_suite_report,"look_degrees":[rad_to_deg(player.rotation.y),rad_to_deg(player.head.rotation.x)],"input_mode":"drag" if player.drag_look_enabled else "pointer","draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"render_primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),"blocked_tower_entries":player.restricted_entry_count,"model":model_statistics,"colliders":collision_info.get("count",0),"evidence_date":"2026-09-22","as_of_date":"2026-10-01"}
  JavaScriptBridge.eval("window.sfState && window.sfState("+JSON.stringify(report)+")")

func _web_command(arguments: Array) -> void:
 if arguments.is_empty():return
 var message = JSON.parse_string(str(arguments[0]))
 if not message is Dictionary:return
 if qa_busy and str(message.get("action","")) not in ["capture"]:return
 match str(message.get("action","")):
  "visit":_begin(clampi(int(message.get("index",1)),0,WAYPOINTS.size()-1))
  "resume":_resume()
  "pause":_pause()
  "drag":_enable_drag_look()
  "pointer_error":
   if pointer_capture_pending > 0.0 and player.active and not menu.visible:
    _enable_drag_look()
  "flight":_toggle_flight()
  "quality":_apply_quality(int(message.get("value",1)))
  "capture":_capture(str(message.get("name","sagrada_familia_web.png")))
  "qa":_qa_action(str(message.get("test","")))
  "photo":
   photo_mode = not photo_mode
   hud.visible = not OS.has_feature("web") and not photo_mode and not menu.visible


func _visitor_snapshot() -> Dictionary:
 var p: Vector3 = player.global_position
 return {"position":[p.x,p.y,p.z],"eye_height":player.camera.global_position.y,"mode":"fly" if player.flight_enabled else "walk","floor":player.is_on_floor() and not player.flight_enabled,"resets":player.reset_count,"uptime":uptime}

func _qa_action(test: String) -> void:
 if not OS.has_feature("web") or not bool(JavaScriptBridge.eval("new URLSearchParams(location.search).get('qa')==='1'")):return
 if test=="suite":
  _run_browser_suite()
  return
 if test in ["glass","tower","tower_boundary"]:
  if not player.flight_enabled:player.set_flight_enabled(true)
  if test=="glass":player.teleport([25,-9,14],[25,-22,17])
  elif test=="tower_boundary":player.teleport([52.5,-10,125],[52.5,0,127])
  else:player.teleport([30,-35,145],[52.5,0,163])
  _resume()
  return
 _resume()
 qa_before = _visitor_snapshot()
 qa_before["test"] = test
 if qa_drive_command!="":Input.action_release(qa_drive_command)
 qa_drive_command = {"forward":"move_forward","up":"fly_up","down":"fly_down"}.get(test,"")
 if qa_drive_command=="":return
 qa_drive_seconds = 2.0 if test=="down" else 3.0
 Input.action_press(qa_drive_command)

func _capture(name: String) -> void:
 var old_hud := hud.visible
 var old_menu := menu.visible
 hud.hide()
 menu.hide()
 await RenderingServer.frame_post_draw
 var image := get_viewport().get_texture().get_image()
 var bytes := image.save_png_to_buffer()
 hud.visible = old_hud
 menu.visible = old_menu
 if OS.has_feature("web"):
  JavaScriptBridge.eval("window.sfCapture("+JSON.stringify(Marshalls.raw_to_base64(bytes))+","+JSON.stringify(name)+")")


func _enable_drag_look() -> void:
 if not ready_to_visit:return
 pointer_capture_pending = 0.0
 pointer_was_captured = false
 player.drag_look_enabled = true
 player.active = true
 started = true
 menu.hide()
 hud.visible = not OS.has_feature("web") and not photo_mode
 Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
 if OS.has_feature("web"):
  JavaScriptBridge.eval("window.sfDragNotice && window.sfDragNotice()")


func _run_browser_suite() -> void:
 if qa_busy:return
 qa_busy = true
 var runner = load("res://scripts/browser_qa.gd").new()
 add_child(runner)
 runner.progress.connect(func(value):qa_progress=value)
 qa_suite_report = await runner.run(self)
 runner.queue_free()
 qa_busy = false
 if OS.has_feature("web"):
  JavaScriptBridge.eval("window.sfSuiteDone && window.sfSuiteDone("+JSON.stringify(qa_suite_report)+")")

func _run_native_qa() -> void:
 var runner = load("res://scripts/browser_qa.gd").new()
 add_child(runner)
 var report: Dictionary = await runner.run(self)
 var file := FileAccess.open(ProjectSettings.globalize_path("res://qa/native_physics.json"),FileAccess.WRITE)
 file.store_string(JSON.stringify(report,"  "))
 get_tree().quit(0 if report.passed else 1)

func _capture_native_views() -> void:
 var output := ProjectSettings.globalize_path("res://../screenshots/realtime")
 DirAccess.make_dir_recursive_absolute(output)
 if "--glass-study" in command_args:
  var views := [
   {"name":"warm_inside","pos":[20,11.5,0],"look":[18.75,22.5,13]},
   {"name":"warm_outside","pos":[20,33.5,0],"look":[18.75,22.5,13]},
   {"name":"cool_inside","pos":[20,-11.5,0],"look":[18.75,-22.5,13]},
   {"name":"cool_outside","pos":[20,-33.5,0],"look":[18.75,-22.5,13]}
  ]
  _visit(6)
  player.active = false
  menu.hide()
  hud.hide()
  for viewpoint in views:
   player.teleport(viewpoint.pos,viewpoint.look)
   for i in range(12): await get_tree().process_frame
   await RenderingServer.frame_post_draw
   var suffix := "_baseline" if "--baseline-glass" in command_args else ""
   var path := output.path_join("glass_study_"+viewpoint.name+suffix+".png")
   get_viewport().get_texture().get_image().save_png(path)
   print("REALTIME_GLASS_CAPTURE ",path)
  get_tree().quit()
  return
 var indices := [0,1,2,3,4,5,6,7,8]
 for argument in command_args:
  if argument.begins_with("--view="): indices = [clampi(int(argument.get_slice("=",1)),0,WAYPOINTS.size()-1)]
 for index in indices:
  _visit(index)
  player.active = false
  menu.hide()
  hud.hide()
  for i in range(12): await get_tree().process_frame
  await RenderingServer.frame_post_draw
  var path := output.path_join("view_%d.png" % index)
  get_viewport().get_texture().get_image().save_png(path)
  print("REALTIME_CAPTURE ",path)
 get_tree().quit()

func _benchmark_native_views() -> void:
 var report := {"engine":Engine.get_version_info().string,"renderer":RenderingServer.get_current_rendering_method(),"adapter":RenderingServer.get_video_adapter_name(),"source":model_source,"resolution":[get_viewport().size.x,get_viewport().size.y],"quality":quality,"frame_cap":Engine.max_fps,"display_server":DisplayServer.get_name(),"window_focus_at_start":get_window().has_focus(),"window_mode":get_window().mode,"method":"Native graphical render process-frame wall-clock intervals; first 45 frames excluded per view; no input claims.","views":[]}
 for index in [0,1,6]:
  _visit(index)
  player.active = false
  menu.hide()
  hud.hide()
  for i in 45: await get_tree().process_frame
  var samples: Array[float] = []
  var last := Time.get_ticks_usec()
  var start := last
  while Time.get_ticks_usec()-start < 5000000:
   await get_tree().process_frame
   var now := Time.get_ticks_usec()
   samples.append(float(now-last)/1000.0)
   last=now
  var mean := 0.0
  for value in samples: mean+=value
  mean/=maxi(1,samples.size())
  samples.sort()
  report.views.append({"index":index,"name":WAYPOINTS[index].name,"window_focus":get_window().has_focus(),"window_visible":get_window().visible,"frames":samples.size(),"mean_ms":mean,"mean_fps":1000.0/maxf(mean,0.01),"p95_ms":samples[int(samples.size()*0.95)],"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"render_primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)})
 var target := ProjectSettings.globalize_path("res://qa/native_graphical_performance.json")
 var file := FileAccess.open(target,FileAccess.WRITE)
 file.store_string(JSON.stringify(report,"  "))
 print("NATIVE_GRAPHICAL_PERFORMANCE ",JSON.stringify(report))
 get_tree().quit()
