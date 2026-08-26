void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    vec2 a = p - vec2(0.30 * aspect, 0.50);
    vec2 b = p - vec2(0.70 * aspect, 0.50);
    bool inside = min(dot(a, a), dot(b, b)) <= 0.13 * 0.13;
    fragColor = vec4(inside ? vec3(0.95) : vec3(0.012), 1.0);
}
