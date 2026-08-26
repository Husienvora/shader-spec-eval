void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.y;
    float aspect = iResolution.x / iResolution.y;
    vec2 p = abs(uv - vec2(0.5 * aspect, 0.68));
    float inside = step(p.x, 0.25) * step(p.y, 0.09);
    fragColor = vec4(mix(vec3(0.012), vec3(0.96, 0.08, 0.86), inside), 1.0);
}
