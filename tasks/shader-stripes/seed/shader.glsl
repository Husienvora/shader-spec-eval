void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    float cell = mod(floor(fragCoord.x / iResolution.x * 6.0), 2.0);
    vec3 col = mix(vec3(0.015), vec3(1.0, 0.05, 0.85), cell);
    fragColor = vec4(col, 1.0);
}
