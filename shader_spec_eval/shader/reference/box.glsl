void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = abs((fragCoord - 0.5 * iResolution.xy) / iResolution.y);
    float inside = step(p.x, 0.30) * step(p.y, 0.15);
    fragColor = vec4(mix(vec3(0.012), vec3(1.0, 0.86, 0.10), inside), 1.0);
}
