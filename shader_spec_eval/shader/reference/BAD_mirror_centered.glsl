void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = abs((fragCoord - 0.5 * iResolution.xy) / iResolution.y);
    float inside = step(p.x, 0.25) * step(p.y, 0.09);
    fragColor = vec4(mix(vec3(0.012), vec3(0.96, 0.08, 0.86), inside), 1.0);
}
