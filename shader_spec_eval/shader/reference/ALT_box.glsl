void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (fragCoord - iResolution.xy * 0.5) / iResolution.y;
    bool inside = all(lessThanEqual(abs(p), vec2(0.30, 0.15)));
    fragColor = vec4(inside ? vec3(1.0, 0.86, 0.10) : vec3(0.012), 1.0);
}
