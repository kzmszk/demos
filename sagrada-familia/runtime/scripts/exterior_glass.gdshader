shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// Exterior only. The approved interior stays on its original StandardMaterial3D.
// Glazing normals are authored outward and preserved through the site mirror.
uniform vec4 original_albedo : source_color = vec4(1.0);
uniform sampler2D original_texture : source_color, hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool use_texture = false;
uniform bool use_vertex_color = false;
uniform bool vertex_color_is_srgb = false;
uniform vec3 uv_scale = vec3(1.0);
uniform vec3 uv_offset = vec3(0.0);

vec3 srgb_to_linear(vec3 value) {
    return mix(value / 12.92, pow((value + vec3(0.055)) / 1.055, vec3(2.4)), step(vec3(0.04045), value));
}

void vertex() {
    UV = UV * uv_scale.xy + uv_offset.xy;
    if (vertex_color_is_srgb) COLOR.rgb = srgb_to_linear(COLOR.rgb);
}

void fragment() {
    vec3 artwork = original_albedo.rgb;
    if (use_texture) artwork *= texture(original_texture, UV).rgb;
    if (use_vertex_color) artwork *= COLOR.rgb;
    ALBEDO = artwork * 0.045 + vec3(0.012, 0.018, 0.022);
    EMISSION = vec3(0.0);
    METALLIC = 0.0;
    ROUGHNESS = 0.22;
    SPECULAR = 0.5;
    CLEARCOAT = 0.25;
    CLEARCOAT_ROUGHNESS = 0.12;
}
