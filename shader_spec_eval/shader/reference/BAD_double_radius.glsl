void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    float a = step(length(uv - vec2(0.30 * aspect, 0.50)), 0.18);
    float b = step(length(uv - vec2(0.70 * aspect, 0.50)), 0.18);
    fragColor = vec4(mix(vec3(0.012), vec3(0.95), max(a, b)), 1.0);
}
