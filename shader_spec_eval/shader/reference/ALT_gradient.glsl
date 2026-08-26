void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float x = clamp(fragCoord.x / iResolution.x, 0.0, 1.0);
    fragColor = vec4(mix(vec3(0.12, 0.0, 0.0), vec3(1.0, 0.06, 0.04), x), 1.0);
}
