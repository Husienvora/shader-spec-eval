void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (fragCoord - iResolution.xy * 0.5) / iResolution.y;
    float d2 = dot(p, p);
    bool inside = d2 >= 0.18 * 0.18 && d2 <= 0.30 * 0.30;
    fragColor = vec4(inside ? vec3(0.10, 0.35, 1.0) : vec3(0.012), 1.0);
}
