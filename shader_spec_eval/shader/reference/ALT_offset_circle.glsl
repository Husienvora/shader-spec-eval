void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    vec2 d = p - vec2(0.30 * aspect, 0.65);
    bool inside = dot(d, d) <= 0.18 * 0.18;
    fragColor = vec4(inside ? vec3(0.96, 0.14, 0.12) : vec3(0.015), 1.0);
}
