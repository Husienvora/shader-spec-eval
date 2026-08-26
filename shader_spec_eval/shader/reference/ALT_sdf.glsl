void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 p = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float inside = 1.0 - step(0.30 * 0.30, dot(p, p));
    fragColor = vec4(mix(vec3(0.02), vec3(1.0, 0.55, 0.08), inside), 1.0);
}
