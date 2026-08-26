void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float r = length(p);
    float ring = step(0.18, r) * step(r, 0.30);
    fragColor = vec4(mix(vec3(0.012), vec3(0.10, 0.35, 1.0), ring), 1.0);
}
