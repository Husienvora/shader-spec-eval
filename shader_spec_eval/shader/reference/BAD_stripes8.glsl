void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float c = mod(floor(fragCoord.x / iResolution.x * 8.0), 2.0);
    fragColor = vec4(mix(vec3(0.015), vec3(1.0, 0.05, 0.85), c), 1.0);
}
